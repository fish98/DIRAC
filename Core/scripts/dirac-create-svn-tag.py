#!/usr/bin/env python
# $HeadURL$
"""
Tag a new release in SVN
"""
__RCSID__ = "$Id$"
from DIRAC import S_OK, S_ERROR, gLogger
from DIRAC.Core.Base      import Script
from DIRAC.Core.Utilities import List, CFG, Distribution

import sys, os, tempfile, shutil, getpass, subprocess

svnProjects = 'DIRAC'
svnVersions = ""
svnUsername = ""
onlyReleaseNotes = False

svnSshRoot = "svn+ssh://%s@svn.cern.ch/reps/dirac/%s"

def setVersion( optionValue ):
  global svnVersions
  svnVersions = optionValue
  return S_OK()

def setProject( optionValue ):
  global svnProjects
  svnProjects = optionValue
  return S_OK()

def setUsername( optionValue ):
  global svnUsername
  svnUsername = optionValue
  return S_OK()

def setOnlyReleaseNotes( optionValue ):
  global onlyReleaseNotes
  gLogger.info( "Only updating release notes!" )
  onlyReleaseNotes = True
  return S_OK()

Script.disableCS()

Script.registerSwitch( "v:", "version=", "versions to tag comma separated (mandatory)", setVersion )
Script.registerSwitch( "p:", "project=", "projects to tag comma separated (default = DIRAC)", setProject )
Script.registerSwitch( "u:", "username=", "svn username to use", setUsername )
Script.registerSwitch( "n", "releaseNotes", "Only refresh release notes", setOnlyReleaseNotes )

Script.parseCommandLine( ignoreErrors = False )

gLogger.info( 'Executing: %s ' % ( ' '.join( sys.argv ) ) )

def usage():
  Script.showHelp()
  exit( 2 )

if not svnVersions:
  usage()

def execAndGetOutput( cmd ):
  p = subprocess.Popen( cmd,
                        shell = True, stdout = subprocess.PIPE,
                        stderr = subprocess.PIPE, close_fds = True )
  stdData = p.stdout.read()
  p.wait()
  return ( p.returncode, stdData )

def getSVNFileContents( projectName, filePath ):
  import urllib2, stat
  gLogger.info( "Reading %s/trunk/%s" % ( projectName, filePath ) )
  viewSVNLocation = "http://svnweb.cern.ch/world/wsvn/dirac/%s/trunk/%s?op=dl&rev=0" % ( projectName, filePath )
  anonymousLocation = 'http://svnweb.cern.ch/guest/dirac/%s/trunk/%s' % ( projectName, filePath )
  for remoteLocation in ( viewSVNLocation, anonymousLocation ):
    try:
      remoteFile = urllib2.urlopen( remoteLocation )
    except urllib2.URLError:
      gLogger.exception()
      continue
    remoteData = remoteFile.read()
    remoteFile.close()
    if remoteData:
      return remoteData
  #Web cat failed. Try directly with svn
  exitStatus, remoteData = execAndGetOutput( "svn cat 'http://svnweb.cern.ch/guest/dirac/%s/trunk/%s'" % ( projectName, filePath ) )
  if exitStatus:
    print "Error: Could not retrieve %s from the web nor via SVN. Aborting..." % fileName
    sys.exit( 1 )
  return remoteData

def generateAndUploadReleaseNotes( projectName, svnPath, versionReleased, singleVersion = False ):
    gLogger.info( "Generating release notes for %s" % projectName )
    fd, rstNotesPath = tempfile.mkstemp()
    Distribution.generateReleaseNotes( projectName, rstNotesPath, versionReleased, singleVersion )
    rstNotesSVNPath = "%s/releasenotes.rst" % ( svnPath )
    svnCmd = "svn import '%s' '%s' -m 'Release notes for version %s'" % ( rstNotesPath, rstNotesSVNPath, versionReleased )
    if os.system( svnCmd ):
      gLogger.error( "Could not upload release notes" )
      sys.exit(1)
    htmlNotesPath = "%s.html" % rstNotesPath
    if Distribution.generateHTMLReleaseNotesFromRST( rstNotesPath, htmlNotesPath ):
      htmlNotesSVNPath = "%s/releasenotes.html" % ( svnPath )
      svnCmd = "svn import '%s' '%s' -m 'HTML Release notes for version %s'" % ( htmlNotesPath, htmlNotesSVNPath, versionReleased )
      if os.system( svnCmd ):
        gLogger.error( "Could not upload release notes" )
        sys.exit(1)
      os.unlink( htmlNotesPath )
    os.unlink( rstNotesPath )
    gLogger.info( "Release notes committed" )
    
##
#End of helper functions
##

#Get username
if not svnUsername:
  svnUsername = getpass.getuser()
gLogger.info( "Using %s as username" % svnUsername )

#Start the magic!
for svnProject in List.fromChar( svnProjects ):

  versionsData = getSVNFileContents( svnProject, "%s/versions.cfg" % svnProject )

  buildCFG = CFG.CFG().loadFromBuffer( versionsData )
  
  upperCaseProject = svnProject.upper()

  if 'Versions' not in buildCFG.listSections():
    gLogger.error( "versions.cfg file in project %s does not contain a Versions top section" % svnProject )
    continue

  versionsRoot = svnSshRoot % ( svnUsername, '%s/tags/%s' % ( svnProject, upperCaseProject ) )
  exitStatus, data = execAndGetOutput( "svn ls '%s'" % ( versionsRoot ) )
  if exitStatus:
    createdVersions = []
  else:
    createdVersions = [ v.strip( "/" ) for v in data.split( "\n" ) if v.find( "/" ) > -1 ]

  for svnVersion in List.fromChar( svnVersions ):

    gLogger.info( "Start tagging for project %s version %s " % ( svnProject, svnVersion ) )

    if "%s_%s" % ( svnProject, svnVersion ) in createdVersions:
      if not onlyReleaseNotes:
        gLogger.error( "Version %s is already there for package %s :P" % ( svnVersion, svnProject ) )
        continue
      else:
        gLogger.info( "Generating release notes for version %s" % svnVersion )
        generateAndUploadReleaseNotes( svnProject, 
                                       "%s/%s_%s" % ( versionsRoot, upperCaseProject, svnVersion ), 
                                       svnVersion )
        continue

    if onlyReleaseNotes:
      gLogger.error( "Version %s is not tagged for %s. Can't refresh the release notes" % ( svnVersion, svnProject ) )
      continue

    if not svnVersion in buildCFG[ 'Versions' ].listSections():
      gLogger.error( 'Version does not exist:', svnVersion )
      gLogger.error( 'Available versions:', ', '.join( buildCFG.listSections() ) )
      continue
    
    versionCFG = buildCFG[ 'Versions' ][svnVersion]
    packageList = versionCFG.listOptions()
    gLogger.info( "Tagging packages: %s" % ", ".join( packageList ) )
    msg = '"Release %s"' % svnVersion
    versionPath = "%s/%s_%s" % ( versionsRoot, upperCaseProject, svnVersion ) 
    mkdirCmd = "svn -m %s mkdir '%s'" % ( msg, versionPath )
    cpCmds = []
    for extra in buildCFG.getOption( 'packageExtraFiles', ['__init__.py', 'versions.cfg'] ):
      source = svnSshRoot % ( svnUsername, '%s/trunk/%s/%s' % ( svnProject, svnProject, extra ) )
      cpCmds.append( "svn -m '%s' copy '%s' '%s/%s'" % ( msg, source, versionPath, extra ) )
    for pack in packageList:
      packVer = versionCFG.getOption( pack, '' )
      if packVer.lower() in ( 'trunk', '', 'head' ):
        source = svnSshRoot % ( svnUsername, '%s/trunk/%s/%s' % ( svnProject, svnProject, pack ) )
      else:
        source = svnSshRoot % ( svnUsername, '%s/tags/%s/%s/%s' % ( svnProject, svnProject, pack, packVer ) )
      cpCmds.append( "svn -m '%s' copy '%s' '%s/%s'" % ( msg, source, versionPath, pack ) )
    if not cpCmds:
      gLogger.error( 'No packages to be included' )
      exit( -1 )
    gLogger.info( 'Creating SVN Dir:', versionPath )
    ret = os.system( mkdirCmd )
    if ret:
      exit( -1 )
    gLogger.info( 'Copying packages: %s' % ", ".join( packageList ) )
    for cpCmd in cpCmds:
      ret = os.system( cpCmd )
      if ret:
        gLogger.error( 'Failed to create tag' )
    
    #Generate release notes for version
    generateAndUploadReleaseNotes( svnProject, versionPath, svnVersion )

