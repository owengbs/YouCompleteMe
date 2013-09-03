#!/usr/bin/env python
#
# Copyright (C) 2011, 2012  Strahinja Val Markovic  <val@markovic.io>
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

import imp
import os
import vim
import ycm_core
from ycm import vimsupport
from ycm import base
from ycm.completers.all.omni_completer import OmniCompleter
from ycm.completers.general.general_completer_store import GeneralCompleterStore


class CompletionRequest( object ):
  def __init__( self, ycm_state ):
    self._completion_start_column = base.CompletionStartColumn()
    self._ycm_state = ycm_state
    self._do_filetype_completion = self._ycm_state.ShouldUseFiletypeCompleter(
      self._completion_start_column )
    self._completer = ( self._ycm_state.GetFiletypeCompleter() if
                        self._do_filetype_completion else
                        self._ycm_state.GetGeneralCompleter() )


  def ShouldComplete( self ):
    return ( self._do_filetype_completion or
             self._ycm_state.ShouldUseGeneralCompleter(
               self._completion_start_column ) )


  def CompletionStartColumn( self ):
    return self._completion_start_column


  def Start( self, query ):
    self._completer.CandidatesForQueryAsync( query,
                                             self._completion_start_column )

  def Done( self ):
    return self._completer.AsyncCandidateRequestReady()


  def Results( self ):
    return self._completer.CandidatesFromStoredRequest()



class YouCompleteMe( object ):
  def __init__( self, user_options ):
    self._user_options = user_options
    self._gencomp = GeneralCompleterStore( user_options )
    self._omnicomp = OmniCompleter( user_options )
    self._filetype_completers = {}
    self._current_completion_request = None


  def CreateCompletionRequest( self ):
    # We have to store a reference to the newly created CompletionRequest
    # because VimScript can't store a reference to a Python object across
    # function calls... Thus we need to keep this request somewhere.
    self._current_completion_request = CompletionRequest( self )
    return self._current_completion_request


  def GetCurrentCompletionRequest( self ):
    return self._current_completion_request


  def GetGeneralCompleter( self ):
    return self._gencomp


  def GetOmniCompleter( self ):
    return self._omnicomp


  def GetFiletypeCompleter( self ):
    filetypes = vimsupport.CurrentFiletypes()

    completers = [ self.GetFiletypeCompleterForFiletype( filetype )
                   for filetype in filetypes ]

    if not completers:
      return None

    # Try to find a native completer first
    for completer in completers:
      if completer and completer is not self._omnicomp:
        return completer

    # Return the omni completer for the first filetype
    return completers[ 0 ]


  def GetFiletypeCompleterForFiletype( self, filetype ):
    try:
      return self._filetype_completers[ filetype ]
    except KeyError:
      pass

    module_path = _PathToFiletypeCompleterPluginLoader( filetype )

    completer = None
    supported_filetypes = [ filetype ]
    if os.path.exists( module_path ):
      module = imp.load_source( filetype, module_path )
      completer = module.GetCompleter( self._user_options )
      if completer:
        supported_filetypes.extend( completer.SupportedFiletypes() )
    else:
      completer = self._omnicomp

    for supported_filetype in supported_filetypes:
      self._filetype_completers[ supported_filetype ] = completer
    return completer


  def ShouldUseGeneralCompleter( self, start_column ):
    return self._gencomp.ShouldUseNow( start_column, vim.current.line )


  def ShouldUseFiletypeCompleter( self, start_column ):
    if self.FiletypeCompletionUsable():
      return self.GetFiletypeCompleter().ShouldUseNow(
        start_column, vim.current.line )
    return False


  def NativeFiletypeCompletionAvailable( self ):
    completer = self.GetFiletypeCompleter()
    return bool( completer ) and completer is not self._omnicomp


  def FiletypeCompletionAvailable( self ):
    return bool( self.GetFiletypeCompleter() )


  def NativeFiletypeCompletionUsable( self ):
    return ( self.CurrentFiletypeCompletionEnabled() and
             self.NativeFiletypeCompletionAvailable() )


  def FiletypeCompletionUsable( self ):
    return ( self.CurrentFiletypeCompletionEnabled() and
             self.FiletypeCompletionAvailable() )


  def OnFileReadyToParse( self ):
    self._gencomp.OnFileReadyToParse()

    if self.FiletypeCompletionUsable():
      self.GetFiletypeCompleter().OnFileReadyToParse()


  def OnBufferUnload( self, deleted_buffer_file ):
    self._gencomp.OnBufferUnload( deleted_buffer_file )

    if self.FiletypeCompletionUsable():
      self.GetFiletypeCompleter().OnBufferUnload( deleted_buffer_file )


  def OnBufferVisit( self ):
    self._gencomp.OnBufferVisit()

    if self.FiletypeCompletionUsable():
      self.GetFiletypeCompleter().OnBufferVisit()


  def OnInsertLeave( self ):
    self._gencomp.OnInsertLeave()

    if self.FiletypeCompletionUsable():
      self.GetFiletypeCompleter().OnInsertLeave()


  def OnVimLeave( self ):
    self._gencomp.OnVimLeave()

    if self.FiletypeCompletionUsable():
      self.GetFiletypeCompleter().OnVimLeave()


  def DiagnosticsForCurrentFileReady( self ):
    if self.FiletypeCompletionUsable():
      return self.GetFiletypeCompleter().DiagnosticsForCurrentFileReady()
    return False


  def GetDiagnosticsForCurrentFile( self ):
    if self.FiletypeCompletionUsable():
      return self.GetFiletypeCompleter().GetDiagnosticsForCurrentFile()
    return []


  def ShowDetailedDiagnostic( self ):
    if self.FiletypeCompletionUsable():
      return self.GetFiletypeCompleter().ShowDetailedDiagnostic()


  def GettingCompletions( self ):
    if self.FiletypeCompletionUsable():
      return self.GetFiletypeCompleter().GettingCompletions()
    return False


  def OnCurrentIdentifierFinished( self ):
    self._gencomp.OnCurrentIdentifierFinished()

    if self.FiletypeCompletionUsable():
      self.GetFiletypeCompleter().OnCurrentIdentifierFinished()


  def DebugInfo( self ):
    completers = set( self._filetype_completers.values() )
    completers.add( self._gencomp )
    output = []
    for completer in completers:
      if not completer:
        continue
      debug = completer.DebugInfo()
      if debug:
        output.append( debug )

    has_clang_support = ycm_core.HasClangSupport()
    output.append( 'Has Clang support compiled in: {0}'.format(
      has_clang_support ) )

    if has_clang_support:
      output.append( ycm_core.ClangVersion() )

    return '\n'.join( output )


  def CurrentFiletypeCompletionEnabled( self ):
    filetypes = vimsupport.CurrentFiletypes()
    filetype_to_disable = self._user_options[
      'filetype_specific_completion_to_disable' ]
    return not all([ x in filetype_to_disable for x in filetypes ])


def _PathToCompletersFolder():
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'completers' )


def _PathToFiletypeCompleterPluginLoader( filetype ):
  return os.path.join( _PathToCompletersFolder(), filetype, 'hook.py' )


