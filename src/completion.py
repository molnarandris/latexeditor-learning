import gi
import re
from gi.repository import GObject
gi.require_version("GtkSource","4")
from gi.repository import GtkSource


'''
    This file is responsible for command completion abilities. I.e. when you start typing 
    \begin{equation}, a small window pops up and gives selectable choices. Usage:
  
        completion = sourceview.get_completion()
        latex_completion_provider = LatexCompletionProvider()
        completion.add_provider(latex_completion_provider)

    That's all. Everything else is taken care by this code (plus GtkSource).
'''

# Just to remember what is whitespace. Used at callbacks wher I don't have control over 
# the input, that's why the extra data input parameter.
def IS_WHITE_SPACE(ch,data):
    if ch == " " or ch == "\n" or ch == "\t": 
        return True
    else:
        return False
        
class LatexCompletionProvider(GObject.GObject, GtkSource.CompletionProvider):
    """
    This is a custom Completion Provider stolen from somewhere. So far it 
    it can do 
        - \begin{equation}
        - \section{}
    Still have to move the cursor to the right place after completion happens.
    Should abstract it, and have some language-independent description of what is 
    a completion. 
    """

    # apparently interface methods MUST be prefixed with do_
    def do_get_name(self):
        # This is the header that is written before the list of choices. 
        return 'Latex'

    # so this defines when to show the completion.
    # I need whenever I type backslash.
    def do_match(self, context):
        # this should evaluate the context to determine if this completion
        # provider is applicable, for debugging always return True
        _,end_iter = context.get_iter()
        buf = end_iter.get_buffer()
        mov_iter = end_iter.copy()
        mov_iter.backward_find_char(IS_WHITE_SPACE,None,None)
        if not mov_iter.equal(buf.get_start_iter()):
            mov_iter.forward_char()
        text = buf.get_text(mov_iter,end_iter,False)
        #print(text)
        if re.match( "\\\\", text):
            mov_iter.forward_char()
            context.text = buf.get_text(mov_iter,end_iter,False)
            return True
        else:
            return False

    # This determines what is being shown. So filtering comes here.
    def do_populate(self, context):
        proposals = [ ]
        
        # If the text contatins \, everything breaks. Let's not handle that situation.
        if re.search("\\\\",context.text):
            return
        # If text is part of begin, show the begin proposal.
        if re.match(context.text,"begin"):
            proposals.append(
	            GtkSource.CompletionItem(label='Equation', text='begin{equation}\n\n\\end{equation}', icon=None, info=None) 
            )
            proposals.append(
	            GtkSource.CompletionItem(label='Itemize', text='begin{itemize}\n\n\\end{itemize}', icon=None, info=None) 
            )
        if re.match(context.text, "section"):
            proposals.append(
                GtkSource.CompletionItem(label='Section', text='section{}', icon=None, info=None), 
            )
        if re.match(context.text, "subsection"):
            proposals.append(
                GtkSource.CompletionItem(label='Subsection', text='subsection{}', icon=None, info=None), 
            )
            
        context.add_proposals(self, proposals, True)
        return
