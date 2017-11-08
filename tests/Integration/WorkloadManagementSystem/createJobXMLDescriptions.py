""" This simply invokes DIRAC APIs for creating 2 jobDescription.xml files,
    one with an application that will end with status 0, and a second with status != 0
"""

from DIRAC.Core.Base.Script import parseCommandLine
parseCommandLine()

from DIRAC.tests.Utilities.utils import find_all
from DIRAC.Interfaces.API.Job import Job


# With a script that returns 0
j = Job()
scriptSHLocation = find_all( 'script-OK.sh', '..', '/DIRAC/WorkloadManagementSystem/JobWrapper' )[0]
j.setExecutable('sh %s' %scriptSHLocation)

jobXMLFile = 'jobDescription-OK.xml'
with open( jobXMLFile, 'w+' ) as fd:
  fd.write( j._toXML() )

# With a script that returns 111
j = Job()
scriptSHLocation = find_all( 'script.sh', '..', '/DIRAC/WorkloadManagementSystem/JobWrapper' )[0]
j.setExecutable('sh %s' %scriptSHLocation)

jobXMLFile = 'jobDescription-FAIL.xml'
with open( jobXMLFile, 'w+' ) as fd:
  fd.write( j._toXML() )

# With a script that returns 1502
j = Job()
scriptSHLocation = find_all( 'script-RESC.sh', '..', '/DIRAC/WorkloadManagementSystem/JobWrapper' )[0]
j.setExecutable('sh %s' %scriptSHLocation)

jobXMLFile = 'jobDescription-FAIL1502.xml'
with open( jobXMLFile, 'w+' ) as fd:
  fd.write( j._toXML() )