#include "slick.sh"
//#include "files.e"

static void getOpenFilenameList(_str (&bufNames)[])
{
   // We will not be appending to the list, so be sure that this gets initialized
   bufNames = null;

   // Get a temp view to loop through the buffers
   orig_wid := _create_temp_view(auto temp_wid);

   // Save the original buffer ID
   origBufID := p_buf_id;

   // Loop through the buffer IDs and get the filenames. Also build a hashtable 
   // of the filenames indexed by the buffer ID.
   for ( ;; ) {
      _next_buffer('nrh');
      if ( p_buf_id==origBufID ) break;

      p_buf_name=p_buf_name; 
      if ( !(p_buf_flags&HIDE_BUFFER) ) {
         bufNames[bufNames._length()] = p_buf_name;
      }
   }

   load_files('+bi 'origBufID);

   _delete_temp_view(temp_wid);

   p_window_id = orig_wid;
}


_command void covdesktop(_str target='thor') name_info(',' VSARG2_MACRO)
{
   int i = 0, p = 0;
   _str filelist = "", cmd = "";
   getOpenFilenameList(auto bufNames);
   for (i = 0; i < bufNames._length(); i++) {
      p = pos('/Users/bpeabody/git/netxtreme/', bufNames[i]);
      if (p > 0) {
         filename = stranslate(bufNames[i], "/git/netxtreme/", "/Users/bpeabody/git/netxtreme/");
         filelist = filelist :+ filename :+ " ";
      }
   }
   reset_next_error();
   clear_all_error_markers();
   clear_pbuffer();
   activate_build();
   if (filelist == "") {
      msg := "No source files are open.  This command only analyzes open buffers."
      concur_command('echo ' :+ msg);
      message(msg);
   } else {
      cmd = '/Users/bpeabody/git/bcm/scripts/vagrant_cov_desktop.sh ' :+ target :+ ' ' :+ filelist :+ ';/Applications/SlickEditPro2019.app/Contents/MacOS/vs "-#covdesktop_done"';
      concur_command(cmd,false,true,false,false);
   }
}

_command void covdesktop_done() name_info(',' VSARG2_MACRO)
{
   set_error_markers();
   refresh('A');
   //maybe goto 1st error
   if ( next_error() ) {
      // or not ..
      bottom_of_window();
      cursor_data();
      _beep();
   } else {
      activate_messages();
   }
}

