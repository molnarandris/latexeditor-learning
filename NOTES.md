# Compilation process

I want async compilation. That is, the UI should not be blocked while compiling -- the user has to be able to still edit. The problem is then that the source buffer gets out-of-sync with the source that was compiled. This makes the log processing and synctexing very hard. Synctex is anyway hard to do between compiles. 

Compilation process

  - Start compile:
    - Save file
    - Compile the saved file (or buffer?)
    
  - Finish compile:
    - Reload the pdf
    - Start processing the log file
    
  - Finish processing log file:
    - Mark errors and warnings in the source buffer. Problem here is that source 
      might have been edited, so the line numbers are not up-to-date. Also the 
      error/warning might not be in the buffer anymore. 
      
  - Synctex (this is instanteneous):
    - Synctex works with the old buffer, not the new one! Have to remember the old one and process the changes
    
    
Hmm now is log processing sync or async? I guess if it gets called at the finish compile state, it does not really matter. However, if at loading I want log file processing, it's better to have that async. Also, if recompile/cancel compile while in log processing, I want to cancel log processing. 

# Synctexing

Synctex does only give line numbers, not columns. There are two standard ways around: either insert newline in the buffer often enough before compile, or try to look for words in both the pdf and the buffer.

Problems with Evince: It does not expose functions to get pointer position in the pdf (all such functions are private). This has to be written by me. Also Evince uses red box for highlighting synctex result -- I want yellow highlight --, but cannot change it. The highlight goes away after clicking the pdf. I want instead it to go away after some time. 

# Pdf viewer

I use Evince. My problems with it:
  - I don't like the Synctex engine
  - I want a zoom to text width feature

Need to add these. First, need to get a function that translates screen position to pdf position. 
  
# Command completion

GtkSource has some implementation for it. For better completion, I need 
