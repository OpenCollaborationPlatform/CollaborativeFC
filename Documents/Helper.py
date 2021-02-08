
from autobahn.wamp import ApplicationError

Key_Not_Available = "key_not_available"

def isOCPError(error, errclass=None, source=None, reason=None):
        
    if not isinstance(error, ApplicationError):
        return False

    uri = error.error
    if not uri.startswith("ocp.error"):
        return False
    
    comps = uri.split(".")
    if errclass and comps[2] != errclass:
            return False
        
    if source and comps[3] != source:
        return False
    
    if reason and comps[4] != reason:
        return False
    
    return True
