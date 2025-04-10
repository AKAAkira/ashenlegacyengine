from battle_participant import Participant
from core import rolldie, autosave
import math

class Battle():
  
  def __init__(self, ui, database, save_state):
    self.DATABASE = database
    self.ui = ui
    self.round_count = 0
    self.save_state = save_state
    self.field_conds = save_state['battle']['field_conds']
    self.participants = dict()
    # save_state['battle']['participants'] holds dict data while self.participants
    # hold Participant data; on save, the latter should be converted to dict and
    # replace save_state['battle']['participants']
    for participant, currvalues in self.save_state['battle']['participants'].items():
      self.participants[participant] = Participant(
        currvalues['refname'], currvalues["team"], self.DATABASE, currvalues
      )
    self.past_dice = save_state['past_dice']
  
  def log(self, *args):
    return self.ui.log(*args)
  
  def rolldie(self, a=1, d=100):
    return self.ui.rolldie(a, d, bank=self.past_dice)
  
  def setup_screen2(self):
    battle_menu = self.ui.generate_menu('battle')
    battle_menu.opts.deploy_participants = (self.deploy_screen, [])
    battle_menu.opts.start_battle = (self.run_battle_simulation, [])
    battle_menu._run_menu()
  
  def deploy_screen(self):
    deploy_menu = self.ui.generate_menu('deployment')
    
    def generate_msg():
      msg = "Current participants:\n"
      if not self.participants:
        return msg + "None\n"
      teams = dict()
      for ptcp, data in self.participants.items():
        if not data:
          continue
        if data.team not in teams:
          teams[data.team] = []
        teams[data.team].append((ptcp, data))
      for team, ptcpsndatas in sorted(teams.items()):
        msg += f"(Team {team}) " + ", ".join(
          f"[{ptcp}]:HP {data.stats['currhp']}" for ptcp, data in ptcpsndatas
        ) + "\n"
      
      return msg
    # deploy_menu.msg = generate_msg
    
    # choice = self.ui.selection(
    #   "Enter command", take_blank=True,
    #   validate=lambda x: x.split()[0] in battle_commands,
    #   validate_message='only takes listed commands'
    # )
    # self.ui.delete_last_line(4+n)
    
    def add_ptcp():
      key = self.ui.get_input('str', input_msg="Enter character database key:")
      team = self.ui.get_input('int', input_msg=f"Enter team # for {key}:")
      # todo, add version differentiation here where:
        # key ending with '-'' lists all available versions if that character
        # key differentiating by '-FE#'' shortcuts to version just before (or after?) that FE
      # if not key in self.DATABASE["character"]:
        # self.log(f"Character {key} not found in the database!\n")
        # return
      ptcpdata = Participant(
        key, team, self.DATABASE
      )
      shorthand = ptcpdata.get_sh()
      if shorthand in self.participants:
        temp = self.participants[shorthand]
        self.participants[shorthand] = None
        if temp:
          self.participants[shorthand + '1'] = temp
          temp.shorthand = shorthand + '1'
        n = 2
        while f"{shorthand}{n}" in self.participants:
          n += 1
        shorthand += str(n)
      self.participants[shorthand] = ptcpdata
      ptcpdata.shorthand = shorthand
      # print('added', self.participants, ptcpdata.team)
    deploy_menu.opts.add = (add_ptcp, [])
    
    edit_menu = self.ui.generate_menu('edit') # ...move to Partcipants.py?
    deploy_menu.opts.edit = (edit_menu._run_menu, [])
        # self.edit_participant(choice[1])
    deploy_menu.opts.remove = (lambda x: x.participants.pop(x.ui.get_input('str', msg="Name participant to remove by key.")), [self])
    deploy_menu.opts.heal_all = (lambda: None, [])
    deploy_menu.opts.reinitialize = (self.__init__, [self.ui, self.DATABASE])
    deploy_menu.opts.remove_koed = (
      lambda: list(
        self.participants.pop(key) for key, ptcp in self.participants.items()
        if ptcp.is_koed()
      ),
      []
    )
    deploy_menu._run_menu(generate_msg)
    self.save_participants()
    autosave(self.save_state, self.ui)
  
  def save_participants(self):
    ptcpdata_dict = dict()
    for key, ptcp in self.participants.items():
      ptcpdata_dict[key] = ptcp.todict()
    
    self.save_state['battle']['participants'] = ptcpdata_dict
  
  def remaining_active_teams(self):
    active_teams = set()
    for ptcpdata in self.participants.values():
      if not ptcpdata.is_koed():
        active_teams.add(ptcpdata.team)
    return len(active_teams)

  def run_battle_simulation(self):
    done = False
    while not done and self.remaining_active_teams() > 1:
      for key, data in self.participants.items():
        for mod, effect in data.onstart:
          pass
          # do effect
      self.new_round()

  def roll_initiative(self):
    curr_max = -math.inf; rolls = []
    self.log("Initiative rolls...")
    for data in self.participants.values():
      if data.is_koed():
        continue
      elif data.state == 'acting':
        self.log(f"{data.get_sh()}: {'+' if data.attack_timing >= 0 else ''}{data.attack_timing}")
        continue
      res1 = sum(rolldie(1, d=100))
      # todo: apply speed statmods - I guess this should happen start of turn though, or at least double-checked then
      # res3 = data.statmods.get('speed', dict()).values()
      res4 = data.statmods.get('initiative', dict()).values()
      res = res1 + data.stats['speed'] + sum(res4) - data.attack_timing
      msg = f"1d100->{res1} + {data.stats['speed']}"
      if res4:
        msg += ' + ' + '+'.join(str(x) for x in res4).replace('+-', '-')
      if data.attack_timing:
        msg += f"-{data.attack_timing}"
      self.log(f"{data.get_sh()}: {msg} = {res}")
      curr_max = max(curr_max, res)
      data.state = 'acting'; rolls.append((data, res))
    for data, res in rolls:
      data.attack_timing = curr_max - res
    return sorted(self.participants.values(), key=lambda x: x.attack_timing)
  
  def new_round(self):
    while True:
      self.round_count += 1; self.log(f"Round {self.round_count}/\n")
      turn_order = self.roll_initiative()
      msg = ', '.join(f"{ptcp.get_sh()} (+{ptcp.attack_timing})" for ptcp in turn_order)
      self.log(f"Order: " + msg)
      while turn_order:
        if turn_order[-1].attack_timing > 99:
          break
        data = turn_order.pop()
        if data.is_koed():
          continue
        # self.deal_effects(data.onturnstart)
        if data.is_koed():
          continue
        move, targets = move_picker(data, allies, enemies)
        if move == 'end':
          break
        self.dealmove(move, targets)
        # self.deal_effects(data.onturnend)
        data.state = 'standby'
      if move == 'end':
        break
  
  def dealmove(self, move, targets):
    if not move.get('attack_multiplier') and not move.get('heal_multiplier'):
      verb = "activates"
    else:
      verb = "uses"
    print(self.get_sh(), verb, move['movename'] + '!')
    if move.get('attack_multiplier'):
      if not any(cond in move['effects'] for cond in ('autohit', 'autocrit')):
        dc_shs = ((target.effectiveevade(), target.get_sh()) for target in targets)
        print(self.get_sh(), "Attack Roll:")
        print("Evasion DC: ", ','.join(f"{dc} ({sh})" for dc, sh in dc_shs))
      else:
        self.log("Evasion: auto-hit")
      
        
      damage_tracker = dict()
      for target in targets:
        damage, critical = move(target, self)
        self.stats["currhp"] = max(0, self.stats["currhp"] - damage)
        if not self.is_koed():
          for func in target.onhit:
            func(self, target)
          if critical:
            target.addpoints('cp', 5)
          else:
            target.addpoints('cp', 1)
        if not self.is_koed():
          for func in self.onstruck:
            func(self, target)
  