# Standard library imports
import uuid

# Local imports
import astrisk
import mylogging

# Start an AGI session
logger = mylogging.ColouredLogger("agi")
agi = astrisk.AGI()

# Start an audio socket server
agi.answer()
try:
    agi.appexec("AudioSocket(" + str(uuid.uuid4()) + ",localhost:1122)")
except:
    pass
    logger.info("AudioSocket is already running")
