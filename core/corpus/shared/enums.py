from enum import Enum

SPLIT_ITEM = ";_DATA_MSG_;"
BUFFER_SIZE = 1024



class ServerCommands(Enum):
    Connect = 0
    Disconnect = 1
    Add_Project = 2
    Remove_Project = 3
    Pull_Project = 4
    Push_Project = 5
    Get_Project_List = 6
    Checkout_Project = 7

class ServerResponses(Enum):
    Success = 0
    Failed = 1
    FTPPath = 2
    ProjectList = 3