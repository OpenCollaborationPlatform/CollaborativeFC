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

#! /usr/bin/env python
import os, glob

qrc_filename = 'resources.qrc'
assert not os.path.exists(qrc_filename)

qrc = '''<RCC version="1.0">
        <qresource prefix="/Collaboration">'''
for fn in glob.glob('Icons/*') + glob.glob('Ui/*.ui') + glob.glob('Ui/*.qml'):
    qrc = qrc + '\n\t\t<file>%s</file>' % fn
    
qrc = qrc + '''\n\t</qresource>\n</RCC>'''

print(qrc)

f = open(qrc_filename,'w')
f.write(qrc)
f.close()

os.system('rcc -binary %s -o resources.rcc' % qrc_filename)
os.remove(qrc_filename)

print("Done compiling")
