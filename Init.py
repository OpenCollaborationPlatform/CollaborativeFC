# ************************************************************************
# *   Copyright (c) Stefan Troeger (stefantroeger@gmx.net) 2019          *
# *                                                                      *
# *   This library is free software; you can redistribute it and/or      *
# *   modify it under the terms of the GNU Library General Public        *
# *   License as published by the Free Software Foundation; either       *
# *   version 2 of the License, or (at your option) any later version.   *
# *                                                                      *
# *   This library  is distributed in the hope that it will be useful,   *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of     *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the      *
# *   GNU Library General Public License for more details.               *
# *                                                                      *
# *   You should have received a copy of the GNU Library General Public  *
# *   License along with this library; see the file COPYING.LIB. If not, *
# *   write to the Free Software Foundation, Inc., 59 Temple Place,      *
# *   Suite 330, Boston, MA  02111-1307, USA                             *
# ************************************************************************

import subprocess

ocp = '/home/stefan/Projects/Go/CollaborationNode/CollaborationNode'

#initialize the ocp node!

#1.Always call init. if already done it will simply fail, otherwise it get initialized
subprocess.call([ocp, 'init'])

#2.Get the connection data
output = subprocess.check_output([ocp, 'config', 'connection.uri'])
ocp_uri = output.decode('ascii').replace('\n', "")
output = subprocess.check_output([ocp, 'config', 'connection.port'])
ocp_port = int(output.decode('ascii').replace('\n', ""))

#3. See if we are up and running
output = subprocess.check_output([ocp])
if len(output.decode('ascii').split('\n')) < 3:
    subprocess.Popen([ocp, 'start'])
