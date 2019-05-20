# google-sheet-scripts
Scripts for doing stuff with google sheets.

# GoogleSheetsDataReplicator
Copies data from on sheet to another.
Need to set   self.configuration_range to the A1 notation of the configuration sheet 
and self.configuration_sheet_id to the ID of the configuration sheet.
Script expects a "Errors" tab on to exist on the configuration sheet and will write processing errors to it.
