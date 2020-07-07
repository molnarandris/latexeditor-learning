# Known Bugs
  
  - The synctex engine as a whole. Evince does not support easy customization. 

# Next things to do

  - Refine the basic command completion. Understand more how it works.
  - On file load, locate all \begin{equation}...\end{equation} and compile the equation 
    to an image.
  - Display the image in the buffer instead of the code
  - When placing the cursor over the image change back to the code
  
  
# Parsing

I think the way to go is to parse the file, and insert tags into the buffer. Then at a given iter one can retreive all tags. What tags do we need? I think this will be refined as I program. Maybe some own hyerarachical tags are needed. For now, wrap the simple equations in a tag. Then I can manipulate how they get displayed.  


# Concrete but not so urgent

  - Some nicer way for the state saver, saving the current file is function calling. Maybe rewrite it to signals.
  - Customize Synctex. Missing Evince functions?? 
 
# Future plans

  - git support
  - Render equations inline
  - Render tikz inline
  - Some drawing thing
  - Possibly a wysiwyg latex editing widget
  
# Parser

  - For completion etc. need some kind of parsing.
  - It shuld do incomplete stuff etc.
  - Should translate between DOM and position in the buffer.
