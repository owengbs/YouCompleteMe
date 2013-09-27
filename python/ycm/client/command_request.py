#!/usr/bin/env python
#
# Copyright (C) 2013  Strahinja Val Markovic  <val@markovic.io>
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

import vim
import time
from ycm.client.base_request import BaseRequest, BuildRequestData, ServerError
from ycm import vimsupport
from ycm.utils import ToUtf8IfNeeded


class CommandRequest( BaseRequest ):
  def __init__( self, arguments, completer_target = None ):
    super( CommandRequest, self ).__init__()
    self._arguments = arguments
    self._completer_target = ( completer_target if completer_target
                               else 'filetype_default' )
    self._is_goto_command = (
        True if arguments and arguments[ 0 ].startswith( 'GoTo' ) else False )
    self._response = None


  def Start( self ):
    request_data = BuildRequestData()
    request_data.update( {
      'completer_target': self._completer_target,
      'command_arguments': self._arguments
    } )
    try:
      self._response = self.PostDataToHandler( request_data,
                                              'run_completer_command' )
    except ServerError as e:
      vimsupport.PostVimMessage( e )


  def Response( self ):
    return self._response


  def RunPostCommandActionsIfNeeded( self ):
    if not self._is_goto_command or not self.Done() or not self._response:
      return

    if isinstance( self._response, list ):
      defs = [ _BuildQfListItem( x ) for x in self._response ]
      vim.eval( 'setqflist( %s )' % repr( defs ) )
      vim.eval( 'youcompleteme#OpenGoToList()' )
    else:
      vimsupport.JumpToLocation( self._response[ 'filepath' ],
                                 self._response[ 'line_num' ] + 1,
                                 self._response[ 'column_num' ] )




def SendCommandRequest( arguments, completer ):
  request = CommandRequest( arguments, completer )
  request.Start()
  while not request.Done():
    time.sleep( 0.1 )

  request.RunPostCommandActionsIfNeeded()
  return request.Response()


def _BuildQfListItem( goto_data_item ):
  qf_item = {}
  if 'filepath' in goto_data_item:
    qf_item[ 'filename' ] = ToUtf8IfNeeded( goto_data_item[ 'filepath' ] )
  if 'description' in goto_data_item:
    qf_item[ 'text' ] = ToUtf8IfNeeded( goto_data_item[ 'description' ] )
  if 'line_num' in goto_data_item:
    qf_item[ 'lnum' ] = goto_data_item[ 'line_num' ] + 1
  if 'column_num' in goto_data_item:
    qf_item[ 'col' ] = goto_data_item[ 'column_num' ]
  return qf_item
