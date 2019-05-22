import os
import pickle
import time

from tendo import singleton

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient import errors as google_errors

class GoogleSheetsDataReplicator:
    def __init__(self, config_sheet_id, auth_file):
        self.credentials = None
        self.service = None
        self.sheets_api = None
        self.source_sheet_index = None
        self.destination_sheet_index = None
        self.task_id_index = None
        self.enable_index = None
        self.tasks = []
        self.configuration_range = 'Configuration!A1:Z50'
        self.configuration_sheet_id = config_sheet_id
        self.credential_token_file = 'token.pickle'
        self.errors = []
        self.auth_file = auth_file

    def run(self):
        self.initialize()
        self.fetch_config_data()
        self.process_tasks()
        self.handle_errors()

    def initialize(self):
        self.get_or_setup_credentials()
        self.setup_service()

    def setup_service(self):
        self.service = build('sheets', 'v4', credentials=self.credentials)
        self.sheets_api = self.service.spreadsheets()

    def get_or_setup_credentials(self):
        self.get_credentials()
        if self.credentials is None: self.setup_credentials()

    def get_credentials(self):
        if os.path.exists(self.credential_token_file):
            with open(self.credential_token_file, 'rb') as token:
                self.credentials = pickle.load(token)

    def setup_credentials(self):
        flow = InstalledAppFlow.from_client_secrets_file(self.auth_file, ['https://www.googleapis.com/auth/spreadsheets'])
        self.credentials = flow.run_local_server()
        with open(self.credential_token_file, 'wb') as token:
            pickle.dump(self.credentials, token)


    def fetch_config_data(self):
        request = self.sheets_api.values().get(spreadsheetId=self.configuration_sheet_id, range=self.configuration_range, majorDimension='ROWS')
        response = self.execute_request(request)
        if not 'values' in response: raise Exception("failed to fetch configuration data")
        for column, value in enumerate(response['values'][0]):
            if value == 'Source Sheet Id': self.source_sheet_index = column
            if value == 'Destination Sheet Id': self.destination_sheet_index = column
            if value == 'ID': self.task_id_index = column
            if value == 'Enable': self.enable_index = column

        self.tasks = response['values'][1:]

    def process_tasks(self):
        for task in self.tasks:
            if task[self.enable_index] != "TRUE": continue
            if (len(task) - 5) % 2 != 0:
                self.add_error(f'Task {task[self.task_id_index]} is not configured properly. Check source and destination pair.')
                continue

            for source_destination_pair in self.get_source_destination_range_pairs(task):
                read_request = self.sheets_api.values().get(spreadsheetId=task[self.source_sheet_index], range=source_destination_pair['source_range'], majorDimension='ROWS', valueRenderOption='UNFORMATTED_VALUE')
                response = self.execute_request_or_log_error(read_request, f"Failed to fetch data for task {task[self.task_id_index]}")
                if response is None: continue

                response['range'] = source_destination_pair['destination_range']
                write_request = self.sheets_api.values().update(spreadsheetId=task[self.destination_sheet_index], range=source_destination_pair['destination_range'], valueInputOption='RAW', body=response)
                self.execute_request_or_log_error(write_request, f"Failed to write data for task {task[self.task_id_index]}")


    @staticmethod
    def get_source_destination_range_pairs(task):
        pairs = []
        for i in range(5, len(task), 2):
            source_range, destination_range = task[i:i + 2]
            pairs.append({ 'source_range': source_range, 'destination_range': destination_range })
        return pairs

    def execute_request_or_log_error(self, request, error_message):
        try:
            return self.execute_request(request)
        except google_errors.HttpError as e:
            self.add_error(f"{error_message}: {e}")
            return None

    def execute_request(self, request):
        try:
            return request.execute()
        except google_errors.HttpError as e:
            if e.resp['status'] == '429':
                # exceeded read or write request quota
                time.sleep(100) # very inefficient but easy
                return self.execute_request(request)
            else:
                raise e

    def add_error(self, message):
        self.errors.append([message])

    def handle_errors(self):
        if len(self.errors) > 0:
            error_range = f"Errors!A1:A{len(self.errors)}"
            body = {
                "range": error_range,
                "majorDimension": "ROWS",
                "values": self.errors
            }
            write_request = self.sheets_api.values().update(spreadsheetId=self.configuration_sheet_id,
                                                            range=error_range,
                                                            valueInputOption='RAW', body=body)
            self.execute_request(write_request)



def run(id, auth_file):
    try:
        me = singleton.SingleInstance()
        GoogleSheetsDataReplicator(id, auth_file).run()
    except singleton.SingleInstanceException:
        pass

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True, help='Sheet ID of the configuration sheet')
    ap.add_argument('--auth', required=False, help='Path to authorization/client secrets json file')

    args = ap.parse_args()
    run(args.id, args.auth)



