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

_command void covdesktop() name_info(',' VSARG2_MACRO)
{
   int i = 0, p = 0;
   _str filelist = "", cmd = "";
   //message("Hello World");
   getOpenFilenameList(auto bufNames);
   for (i = 0; i < bufNames._length(); i++) {
      p = pos('/Users/bpeabody/git/netxtreme/', bufNames[i]);
      if (p > 0) {
         filename = stranslate(bufNames[i], "/git/netxtreme/", "/Users/bpeabody/git/netxtreme/");
         filelist = filelist :+ filename :+ " ";
      }
      //messageNwait(bufNames[i]);
   }
   //messageNwait(filelist);
   cmd = '/Users/bpeabody/git/bcm/scripts/vagrant_cov_desktop.sh ' :+ filelist;
   execute('clear-pbuffer');
   concur_command(cmd,false,true,false,false);

}

