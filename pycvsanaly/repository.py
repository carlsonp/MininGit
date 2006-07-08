# Copyright (C) 2006 Libresoft
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors : 
#       Alvaro Navarro <anavarro@gsyc.escet.urjc.es>
#       Gregorio Robles <grex@gsyc.escet.urjc.es>

"""
Abastract class that implements basic methods to work with
repositories

@author:       Alvaro Navarro and Gregorio Robles
@organization: Grupo de Sistemas y Comunicaciones, Universidad Rey Juan Carlos
@copyright:    Universidad Rey Juan Carlos (Madrid, Spain)
@license:      GNU GPL version 2 or any later version
@contact:      anavarro,grex@gsyc.escet.urjc.es
"""

import os
import sys
import re

from commiter import Commiter
from directory import *
from files import File
from commit import Commit
from config_files import *

file_properties = {'file_id':'',
                   'name': '',
                   'filetype' :'',
                   'creation_date': '',
                   'last_modification': '',
                   'module_id':'',
                   'size':''}

directory_properties = {'module_id':'',
                        'module':''}

commit_properties = {'commit_id':'',
                     'file_id':'',
                     'commiter_id':'',
                     'revision':'',
                     'plus':'',
                     'minus':'',
                     'inattic':'',
                     'cvs_flag':'',
                     'external':'',
                     'date_log':'',
                     'filetype':'',
                     'module_id':''}

class RepositoryFactory:
    """
    Basic Factory that abastracts the process to create new repositories
    """
    def create(type):
        if type.upper() == "CVS":
            return RepositoryCVS()
        if type.upper() == "SVN":
            return RepositorySVN()

    # We make it static
    create = staticmethod(create)


class Repository:
    """
    Generic class with basic information
    """

    def __init__(self):
        pass

    def log(self):
        pass

    def analyseFile(self,file):
        """
        Given a filename, returns what type of file it is.
        The file type is set in the config_files configuration file
        and usually this depends on the extension, although other
        simple heuristics are used.

        @type  file: string
        @param file: filename

        @rtype: string
        @return: file type id (see config_files_names for transformation into their names: documentation => 0, etc.)
        """
        i = 0
        for fileTypeSearch_list in config_files_list:
                for searchItem in fileTypeSearch_list:
                        if searchItem.search(file.lower()):
                                return i
                i+=1
        # if not found, specify it as unknown
        return config_files_names.index('unknown')


    def clean_properties(self):

        k = directory_propierties.getkeys()
        
            
    def isFileInAttic(self,file):
        """
        Looks if a given file is in the Attic
        
        In CVS a file is in the Attic if it has been removed from the
        working copy
        
        @type  file: string
        @param file: name of the file
        
        @rtype: int (boolean)
        @return: 1 if file is in Attic, else 0
        """
        if re.compile('/Attic/').search(file):
            return 1
        else:
            return 0

    def countLOCs(self,filename):
        """
        CVS does not count the initial lenght of a file that is imported
        into the repository. In order to have a real picture a measure
        of the file size at a given time is needed.

        This function returns (if possible) the current size of the
        file in LOC (_with_ comments and blank lines) as wc would do
        In order to have the length for the imported version all the
        changes will have to be added (if removed lines) or subtracted
        (added lines)

        @type  filename: string
        @param filename: Name of the file that should be counted

        @rtype: int
        @return: number of LOCs
        """
        try:
                result = len(open(filename).readlines())
        except IOError:
                result = 0
        return result

    def commitersmodule2sql(self, db, comms):
        """
        @type  db: Database object
        @param db: Object that represents connection with a database

        @type comms: dictionary
        @param comms: list of commiters

        """
        for co in comms:
            for i in comms[co]:
                query = "INSERT INTO commiters_module (commiter_id,module_id) VALUES ('"
                query += str(i) + "','" + str(co) + "');"

                db.insertData(query)

    def commiters2sql(self, db, comms):
        """
        @type  db: Database object
        @param db: Object that represents connection with a database

        @type comms: dictionary
        @param comms: list of commiters
        """
        for co in comms:
            query = "INSERT INTO commiters (commiter_id, commiter) VALUES ('"
            query += str(comms[co]) + "','" + str(co) + "');"

            db.insertData(query)


class RepositoryCVS(Repository):
    """
    Child Class that implements CVS Repository basic access
    """

    def __init__(self):
        pass

    def log(self,db, logfile=''):

        if logfile:
            linelog = open(logfile,'r')
        else:
            linelog = os.popen3 ('/usr/bin/cvs -z9 -Q log -N .')

        filename = ''
        dirname = ''
        commitername = ''
        modificationdate = ''
        revision = ''
        plus = ''
        minus = ''
        sum_plus = 0
        sum_minus = 0
        isbinary = 0
        inAttic = 0
        isbinary =0
        cvs_flag= 0
        newcommit = 0
        external = 0
        checkin= 0

        logtxt_flag = 0

        authors = {}
        modulecommiters = {}
        actualcommiters = []
        commits = []

        f = None
        c = None

        mtree = tree(0)

        while 1:
            if logfile:
                line = linelog.readline()
            else:
                line = linelog[1].readline()
            if not line:
                break
            else:
                line = line[:-1]
                pattern0 = re.compile("^RCS file: (.*)")
                pattern1 = re.compile("^Working file: (.*)")
                pattern2 = re.compile("^keyword substitution: b")
                pattern3 = re.compile("^revision ([\d\.]*)")
                #pattern4 = re.compile("^date: (\d\d\d\d)[/-](\d\d)[/-](\d\d) (\d\d:\d\d:\d\d)(.*);  author: (.*);  state: (.*);  lines: \+(.*) -(.*)")
                pattern4 = re.compile("^date: (\d\d\d\d)[/-](\d\d)[/-](\d\d) (\d\d:\d\d:\d\d)(.*);  author: (.*);  state: (.*);  lines: \+(\d*) -(\d*)")
                pattern5 = re.compile("^date: (\d\d\d\d)[/-](\d\d)[/-](\d\d) (\d\d:\d\d:\d\d)(.*);  author: (.*);  state: ")
                pattern6 = re.compile("^CVS_SILENT")
                pattern7 = re.compile("patch(es)?\s?.* from |patch(es)?\s?.* by |patch(es)?\s.*@|@.* patch(es)?|'s.* patch(es)?|s' .* patch(es)?|patch(es)? of | <.* [Aa][Tt] .*>| attached to #")
                pattern8 = re.compile("^----------------------------")
                pattern9 = re.compile("^========================================")

                mobj0 = pattern0.match(line)
                if mobj0:

                    inAttic = self.isFileInAttic(mobj0.group(1))
                    isbinary = 0
                    newcommit = 0 
                    cvs_flag = 0
                    revision = ''
                    sum_plus = 0
                    sum_minus = 0
                    external = 0
                    plus = '0'
                    minus = '0'
                    modificationdate = ''
                    creationdate = ''
                    commits = []
                    actualcommiters = []
                    filepath = ''
                    #filename = ''

                mobj1 = pattern1.match(line)
                if mobj1:

                    # Directory and File
                    fileraw = mobj1.group(1)
                    fileraw = fileraw.replace("'","\\'")

                    filename = fileraw.split('/')[-1]
                    filepath = fileraw[:-len(filename)]
                    filetype = self.analyseFile(filename)

                    if not filepath:
                        filepath = '/'
                    mtree.addDirectory(filepath)

                    file_properties['name'] = filename
                    file_properties['filetype'] = filetype
                    file_properties['module_id'] = str(mtree.getid(filepath))
                    file_properties['filetype'] = filetype

                    f = File()

                mobj2 = pattern2.match(line)
                if mobj2:
                    isbinary = 1

                mobj3 = pattern3.match(line)
                if mobj3:
                    revision = mobj3.group(1)

                mobj4 = pattern4.match(line)
                if mobj4:

                    
                    if not filepath:
                        filepath = '/'

                    # Commiter and Date
                    year       = mobj4.group(1)
                    month      = mobj4.group(2)
                    day        = mobj4.group(3)
                    rest_date  = mobj4.group(4)

                    creationdate = (year + "-" + month + "-" + day + " " + rest_date)

                    if not modificationdate:
                        modificationdate = creationdate

                    # Create new Commiter object
                    commitername =  mobj4.group(6)
                    if not authors.has_key(commitername):
                        authors[commitername] = len(authors)

                    if not authors[commitername] in actualcommiters:
                        actualcommiters.append(authors[commitername])

                    plus       = mobj4.group(8)
                    minus      = mobj4.group(9)
                    sum_plus  += int(plus)
                    sum_minus += int(minus)

                    if isbinary:
                        plus = "0"
                        minus = "0"

                    newcommit = 1
                    logtxt_flag = 1
                    logtxt = ''

                mobj5 = pattern5.match(line)
                if mobj5:
                    if not filepath:
                        filepath = '/'

                    # Date
                    year       = mobj5.group(1)
                    month      = mobj5.group(2)
                    day        = mobj5.group(3)
                    rest_date  = mobj5.group(4)

                    creationdate = (year + "-" + month + "-" + day + " " + rest_date)

                    if not modificationdate:
                        modificationdate = creationdate
                        
                    # Create new Commiter object
                    commitername =  mobj5.group(6)
                    if not authors.has_key(commitername):
                        authors[commitername] = len(authors)

                    if not authors[commitername] in actualcommiters:
                        actualcommiters.append(authors[commitername])

                    newcommit = 1
                    logtxt_flag = 1
                    logtxt = ''
                    
                mobj6 = pattern6.match(line)
                if mobj6:
                    cvs_flag = 1

                mobj7 = pattern7.match(line)
                if mobj7:
                    external = 1

                mobj8 = pattern8.match(line)
                mobj9 = pattern9.match(line)
                if mobj9:
                    newcommit = 0

                if mobj9 and not isbinary and not inAttic:
                    checkin = self.countLOCs(filepath + "/" + filename)
                    checkin = checkin - sum_plus + sum_minus
                    plus    = str(checkin)
                    minus   = "0"

                if (mobj8 and newcommit) or mobj9:
                    if revision != "1.1.1.1" and revision != "":
                        if not modificationdate:
                            modificationdate = creationdate
                        commit_properties['file_id'] = str(f.get_id())
                        commit_properties['commiter_id'] = str(authors[commitername])
                        commit_properties['revision'] = str(revision)
                        commit_properties['plus'] = str(plus)
                        commit_properties['minus'] = str(minus)
                        commit_properties['inattic'] = str(inAttic)
                        commit_properties['cvs_flag'] = str(cvs_flag)
                        commit_properties['external'] = str(external)
                        commit_properties['date_log'] = str(creationdate)
                        commit_properties['filetype'] = str(filetype)
                        commit_properties['module_id'] = str(mtree.getid(filepath))
                        c = Commit(commit_properties)
                        file_properties['size'] = str(checkin)
                        file_properties['creation_date'] = str(creationdate)
                        file_properties['last_modification'] = str(modificationdate)
                        f.add_properties(file_properties)

                        modulecommiters[mtree.getid(filepath)] = actualcommiters
                        # End of commit
                        newcommit = 0
                        modificationdate = ""
        try:
            # Files
            f.files2sql(db)
            # Directories
            mtree.tree2mysql(db,mtree.root,"",0,"")
            # Commiters
            self.commiters2sql(db,authors)
            # Commits
            c.commits2sql(db)
            # Commiters-module
            self.commitersmodule2sql(db, modulecommiters)
        except:
            sys.exit("Cannot get log! maybe this is not a CVS/SVN work directory or you have problems with your connection\n")

        if logfile:
            linelog.close()

class RepositorySVN(Repository):
    """
    Child Class that implements SVN Repository basic access
    """

    def __init__(self):
        pass

    def checkout(self):
        """
        SVN Checkout
        """
        os.chdir(self.src_dir);

        os.system('svn co --revision {' + str(self.date) + '} ' +  self.repository)