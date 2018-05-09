from enum import Enum

SPLIT_ITEM = ";_DATA_MSG_;"
BUFFER_SIZE = 4096



class ServerCommands(Enum):
    Connect = 0
    Disconnect = 1
    Commit_Inquiry = 2
    Commit_Finished = 3
    Remove_Project = 4
    Check_Out_Inquiry = 5
    Get_Project_List = 7
    Check_In_Project = 8
    Download_Project = 9

class ServerResponses(Enum):
    Success = 0
    Failed = 1
    FTPPath = 2
    ProjectList = 3