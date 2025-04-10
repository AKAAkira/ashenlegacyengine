import sys

class UI():
  
  def __init__(self, metadata):
    self.width = metadata["width"]
    self.f_obj = None
    self.commands = []
    self.last_autosave = metadata["last_autosave"]
    self.open(metadata["logfilename"])
  
  def __enter__(self):
    # self.open(self.fname)
    return self
  
  def __exit__(self, exc_type, exc_val, exc_tb):
    self.close()
  
  def metadata(self):
    return {"width": self.width, "last_autosave": self.last_autosave, "logfilename": self.fname}
  
  def delete_last_line(self, n=1): # https://stackoverflow.com/questions/19596750/is-there-a-way-to-clear-your-printed-text-in-python
    """Delete the last line(s) in the STDOUT."""
    
    # input(f"Removing {n}+1 lines..."); n += 1
    for _ in range(n):
      sys.stdout.write("\x1b[1A")  # cursor up one line
      sys.stdout.write("\x1b[2K")  # delete the last line
  
  def get_input(self, category, sel_list=[], msg="", input_msg=None):
    """Get input from the user, with the valid categories of
    selection, str, int, and yesno.
    Initially meant to take comments, but that's probably best left for the "Press Enter to continue" function."""
    
    is_valid = False
    input_msg = (input_msg or {
      "selection": "Enter selection (# or exact term): ",
      "str": "Enter string:",
      "int": "Enter integer:",
      "yesno": "Enter y/n:"
    }[category]) + '\n'
    
    command = ""
    while not command:
      n = 0
      if not self.commands:
        if msg:
          n = self.log(msg + '\n')
        if category == 'selection':
          n = self.log("Choices:")
          n += self.log(' '.join(f"{n+1}:{item}" for n, item in enumerate(sel_list)) + '\n')
        self.commands = input(input_msg).split()[::-1]
        self.delete_last_line(n + 2)
      command = self.commands.pop()
      if command.startswith('>'):
        comment = ' '.join([command[1:]] + self.commands[::-1])
        if comment.find('\n') + 1:
          comment, self.commands = comment.split('\n', 1)
          self.commands = self.commands.split()[::-1]
        else:
          self.commands = []
        self.delete_last_line()
        self.log(comment + '\n'); command = ""
      elif category == 'selection':
        is_valid = command.isdecimal() and 0 < int(command) < len(sel_list) + 1
        if is_valid:
          command = list(sel_list)[int(command) - 1]
          continue
        is_valid = command.lower() in sel_list
      elif category == 'int':
        is_valid = command[1 if command[0] in ('+', '-') else 0:].isdecimal()
        if is_valid:
          command = int(command)
      elif category == 'yesno':
        command = command[0].lower()
        is_valid = command in ('y', 'n')
      elif category == 'str':
        is_valid = True
      if not is_valid:
        input_msg = f"Invalid choice: {command} for {category}!\n" + input_msg
        command = ''; self.commands = []
    
    return command
  
  # note: deprecated, getting around to converting all instances to get_input
  def selection(
    self, msg, domain=(), take_blank=False,
    validate=lambda x: x.isdigit() or not x,
    validate_message='only supports integers'
  ):
    choice = ''; tries = 0; cont = True
    if domain and take_blank:
      domain += ('',)
    while cont:
      tries += msg.count('\n') + 1; choice = input(msg+'>')
      self.delete_last_line()
      # if choice.split().strip()[0] in commands and validate_command(choice):
      #   break
      if not choice and not take_blank:
        print("Empty choice not supported here.")
      elif validate and validate_message and not validate(choice):
        print("Not supported selection:", choice, f"({validate_message})")
      elif domain and choice not in domain:
        print("Invalid response:", choice)
      else:
        cont = False
    
    self.delete_last_line(tries - 1)
    return choice

  def print_tabs(self, paged_dict):
    page = 1
    while page:
      for line in paged_dict[page]:
        print(line)
      next_page = self.selection(
        f"Pick page out of {tuple(paged_dict)}, or exit with empty ENTER",
        domain=tuple(str(key) for key in paged_dict), take_blank=True
      )
      self.delete_last_line(len(paged_dict[page]))
      page = int(next_page) if next_page else next_page

  def print_rows(self, itemlist):
    for x in range((len(itemlist) - 1) // 4 + 1):
      print(*itemlist[x*4:x*4+4])
    
    return (len(itemlist) - 1) // 4 + 1
  
  def open(self, logfilename=''):
    if self.f_obj:
      self.close()
    self.fname = logfilename
    if self.fname:
      self.f_obj = open(self.fname, 'a')
    else:
      self.f_obj = None
  
  def close(self):
    if self.f_obj:
      self.f_obj.close()
  
  def log(self, msg):
    n = 1
    while len(msg.replace('\n', '')) > self.width:
      n += 1
      cutoff = (msg[:self.width] + '\n').find('\n')
      space = msg[:cutoff].rfind(' ')
      if space < 0:
        space = cutoff
      print(msg[:space])
      if self.f_obj:
        self.f_obj.write(msg[:space] + '\n')
      msg = msg[space:].strip()
    n += msg.count('\n'); print(msg)
    if self.f_obj:
      self.f_obj.write(msg + '\n')
    
    return n
  
  # def present_menu(self, options):
    # """Menu screen implementation attempt where options is a dict; likely
# would not have worked as contained functions can't self-reference"""
    # choice = self.get_input('selection', options)
    # options[choice][0](*options[choice][1])
  
  def generate_menu(self, name):
    return Menu(name, self)

class Options():
  pass

class Menu():
    
  def __init__(self, name, ui_obj):
    self.name = name
    self.ui_obj = ui_obj
    self.disabled = set(); self.disabled.add('')
    self.opts = Options()
  
  def disable(self, *args):
    if len(args) == 1:
      self.disabled.add(str(args[0]))
    else:
      self.disabled.update(str(arg) for arg in args)
  
  def _run_menu(self, msg_func=None):
    choice = ""; options = vars(self.opts)
    while not choice:
      n = self.ui_obj.log(f"{self.name} menu:\n")
      if msg_func:
        n += self.ui_obj.log(msg_func() + '\n')
      while choice in self.disabled:
        n2 = self.ui_obj.log(f"{choice} is currently disabled!") if choice else 0
        choice = self.ui_obj.get_input(
          'selection', options | {"exit": tuple()}
        )
        # print(self.disabled); input()
        self.ui_obj.delete_last_line(n2)
      self.ui_obj.delete_last_line(n)
      if choice.lower() != 'exit':
        # items in the tuple/list "action" should be ordered func, then args, then maybe help message
        action = options.get(choice)
        func, args = action[0], action[1]
        if len(action) > 2:
          assert len(action) < 4
          help = action[2]
        func(*args)
        # loop if not one-off menu
        choice = ""
    
    # input("Exiting, press ENTER to close...")
