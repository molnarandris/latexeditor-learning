import gi
import re
from gi.repository import GObject, Gtk
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

ENVIRONMENTS = [
    'equation', 
    'equation*', 
    'itemize',
    'enumerate',
    'tikzpicture',
]

ENV_PROPOSALS = [ GtkSource.CompletionItem(
        label = e,
        text =  'begin{' + e + '}\n  •\n\\end{' + e +  '}',
        icon = None,
        info = None,  
    )
    for e in ENVIRONMENTS
]

SECTIONS = [
    'part',
    'chapter',
    'section',
    'subsection',
    'subsubsection',
    'paragraph'
    'subparagraph',
]

SEC_PROPOSALS = [ GtkSource.CompletionItem(
        label = s,
        text =  '\\' + s + '{•}',
        icon = None,
        info = None,  
    )
    for s in SECTIONS
]



PROPOSALS = ENV_PROPOSALS + SEC_PROPOSALS

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
        proposals = [ p for p in PROPOSALS if p.get_text().startswith(context.text)]
        context.add_proposals(self, proposals, True)
        return
        
    # If matched, display proposal and set selection to around the dot.
    def do_activate_proposal(self,proposal,it):
        buf = it.get_buffer()
        mov_iter = it.copy()
        mov_iter.backward_find_char(lambda ch,data: ch=='\\',None,None)
        mark = buf.create_mark(None,mov_iter,True)
        mov_iter.forward_char()
        buf.delete(mov_iter,it)
        buf.insert(it,proposal.get_text())
        mov_iter = buf.get_iter_at_mark(mark)
        if it.backward_find_char(lambda ch,data: ch == '•',None,mov_iter):
            mov_iter = it.copy()
            mov_iter.forward_char()
            buf.select_range(it,mov_iter)
        return True
      
                
