from battle_participant import Participant
from core import rolldie, autosave
from itertools import (
  batched as iterbatch, chain as iterchain,
  product as iterprod, zip_longest as iterzip
)
import math, re

class Battle():
  
  def __init__(self, ui, database, save_state):
    self.DATABASE = database
    self.ui = ui
    self.round_count = 0
    self.save_state = save_state
    self.field_conds = {"endcon": "one_remaining_team"}
    # TODO: convert non-function items in save_state['battle']['field_conds'] into this
    self.participants = dict()
    # save_state['battle']['participants'] holds dict data while self.participants
    # hold Participant data; on save, the latter should be converted to dict and
    # replace save_state['battle']['participants']
    for participant, currvalues in self.save_state['battle']['participants'].items():
      self.participants[participant] = Participant(
        currvalues['refname'], currvalues["team"], self, currvalues
      )
    self.past_dice = save_state['past_dice']
  
  def endcon(self):
    """Check if the battle is over."""

    endcon_list = {
      "one_remaining_team": lambda: self.remaining_active_teams() < 2,
    }

    return endcon_list[self.field_conds["endcon"]]()

  
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
    
    def get_teamsorted():
      teams = dict()
      for ptcp in self.participants.values():
        if not ptcp:
          continue
        if ptcp.team not in teams:
          teams[ptcp.team] = []
        teams[ptcp.team].append(ptcp)
      
      return teams
    
    def generate_msg():
      msg = "Current participants:\n"
      if not self.participants:
        return msg + "None\n"
      teams = get_teamsorted()
      for team, ptcps in sorted(teams.items()):
        msg += f"(Team {team}) " + ", ".join(
          f"[{ptcp.get_sh()}]:HP {ptcp.stats['currhp']}" for ptcp in ptcps
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
      key = ""; n = 0
      while not key:
        key = self.ui.get_input('str', input_msg="Enter character database key:")
        self.ui.delete_last_line(n)
        if not key in self.DATABASE['character']:
          n = self.log(f"Character refname {key} not foundin database!")
          key = ""
      team = self.ui.get_input('int', input_msg=f"Enter team # for {key}:")
      # todo, add version differentiation here where:
        # key ending with '-'' lists all available versions if that character
        # key differentiating by '-FE#'' shortcuts to version just before (or after?) that FE
      # if not key in self.DATABASE["character"]:
        # self.log(f"Character {key} not found in the database!\n")
        # return
      ptcp = Participant(
        key, team, self
      )
      shorthand = ptcp.get_sh()
      if shorthand in self.participants:
        if self.participants[shorthand] != None:
          tempdata = self.participants[shorthand]
          self.participants[shorthand] = None
          self.participants[shorthand + '1'] = tempdata
          tempdata.shorthand = shorthand + '1'
        n = 2
        while f"{shorthand}{n}" in self.participants:
          n += 1
        shorthand += str(n)
      self.participants[shorthand] = ptcp
      ptcp.shorthand = shorthand
      # print('added', self.participants, ptcpdata.team)
    deploy_menu.opts.add = (add_ptcp, [])
    
    edit_menu = self.ui.generate_menu('edit') # ...move to _partcipant.py?
    deploy_menu.opts.edit = (edit_menu._run_menu, [])
        # self.edit_participant(choice[1])
    deploy_menu.opts.remove = (
      lambda: self.participants.pop(self.ui.get_input(
        'str', msg="Name participant to remove by key."
      )), []
    )
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
    teams = get_teamsorted()
    self.participants = {
      ptcp.get_sh(): ptcp for ptcp in
      iterchain(*(ptcps for team, ptcps in sorted(teams.items())))
    }
    self.save_participants(); self.update_save_state()
    autosave(self.save_state, self.ui)
  
  def save_participants(self):
    ptcpdata_dict = dict()
    for key, ptcp in self.participants.items():
      ptcpdata_dict[key] = ptcp.todict()
    
    self.save_state['battle']['participants'] = ptcpdata_dict

  def update_save_state(self):
    # self.save_state['battle']['field_conds'] = {
    #   key: func if callable(func) else func for key, func in self.field_conds.items()
    # }
    self.save_state['past_dice'] = self.past_dice
    self.save_state['battle']['round_count'] = self.round_count
  
  def remaining_active_teams(self):
    active_teams = set()
    for ptcp in self.participants.values():
      if not ptcp.is_koed():
        active_teams.add(ptcp.team)
    # print("Active teams:", active_teams); input()
    return len(active_teams)

  def run_battle_simulation(self):
    while not self.endcon():
      for key, data in self.participants.items():
        for mod, effect in data.onstart:
          pass
          # do effect
      self.new_round()
    self.log("Combat over.\n")
    self.update_save_state()
    autosave(self.save_state, self.ui)

  def roll_initiative(self):
    curr_max = -math.inf; rolls = []
    self.log("Initiative rolls...")
    for data in self.participants.values():
      if data.is_koed():
        continue
      elif data.state == 'acting':
        data.attack_timing -= 100
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
        msg += f" - {data.attack_timing}"
      self.log(f"{data.get_sh()}: {msg} = {res}")
      curr_max = max(curr_max, res)
      data.state = 'acting'; rolls.append((data, res))
    if curr_max == -math.inf:
      first_move = min(ptcp.attack_timing for ptcp in self.participants.values())
      for ptcp in self.participants.values():
        assert ptcp.state == "acting"
        ptcp.attack_timing -= first_move
    else:
      for ptcp, res in rolls:
        ptcp.attack_timing = curr_max - res
    return sorted(self.participants.values(), key=lambda ptcp: ptcp.attack_timing)
  
  def new_round(self):
    self.round_count += 1; self.log(f"Round {self.round_count}/\n")
    turn_order = self.roll_initiative()
    msg = ', '.join(
      f"{ptcp.get_sh()} (+{ptcp.attack_timing})"
      for ptcp in turn_order if not ptcp.is_koed()
    )
    self.log(f"Order: " + msg + '\n')
    turn_order = turn_order[::-1]
    while turn_order:
      if self.endcon():
        self.log("Combat Over.\n")
        break
      if turn_order[-1].attack_timing > 99:
        break
      data = turn_order.pop()
      if data.is_koed():
        continue
      # self.deal_effects(data.onturnstart)
      if data.is_koed():
        continue
      move = data.action_menu()
      if not move:
        self.log(f"{data.get_sh()} passes...\n")
      else:
        targets = self.get_move_targets(move, data.team)
        for target in targets:
          pass # check if each has before_hit mods
        if move == 'end':
          break
        self.dealmove(data, move, targets)
        # self.deal_effects(data.onturnend)
      data.state = 'standby'
      if move == 'end':
        break
  
  def get_move_targets(self, move, team):
    targets = []; cmd = ""
    aoe = {
      # once coordinate system is in place this'll have to be replaced by aoe size rather than max targets
      # though it might be worth keeping both to switch between manual and automatic targeting modes
      "single": 1,
      "small": 3,
      "medium": 4,
      "large": 5, # assumption
      "extralarge": 6 # assumption
    }
    max_targets = aoe.get(move["default_target"][1], len(self.participants))
    
    def valid_target(target_team):
      # todo: damage dealers target opponents, heals target teammates
      # this can get reversed like with the Charm status condition
      return target_team != team
    
    while cmd != "done":
      n = self.log(f"Current targets: {', '.join(targets) or None}\n")
      cmd = self.ui.get_input("selection", list(
        key for key, ptcp in self.participants.items()
        if valid_target(ptcp.team)
      ) + ["done"])
      self.ui.delete_last_line(n)
      if cmd == "done":
        continue
      if cmd in targets:
        targets.remove(cmd)
      else:
        targets.append(cmd)
    if len(targets) > max_targets:
      self.log(f"Max target count exceeded, dropping {targets[max_targets:]}.")
      targets = targets[:max_targets]
    
    return list(self.participants[target] for target in targets)
  
  def dealmove(self, ptcp, move, targets):
    if move.get('attack_multiplier') or move.get('heal_multiplier'):
      verb = "uses"
    else:
      verb = "activates"
    self.log(f"{ptcp.get_sh()} {verb} {move['movename']}!\n")
    if move.get('attack_multiplier'):
      hit_bank = {"hit": [], "crit": [], "miss": []}
      hit_bank_reverse = dict((target, list()) for target in targets)
      if not 'autohit' in move['effects']:
        # todo: calculate bonuses
        # todo also: arts attacks and magic evasion
        hit_rolls = rolldie(move.get('hit_number', 1) * len(targets), d=100)
        hit_stat = (
          ptcp.stats['melee'] if "melee" in move["attack_type"]
          else ptcp.stats['ranged']
        )
        hit_bonuses = []
        hit_total = hit_stat + sum(item[0] for item in hit_bonuses)
        hit_totals = (hit_roll + hit_total for hit_roll in hit_rolls)
        if move.get('hit_number', 1) > 1:
          hit_totals = iterbatch(hit_totals, move.get('hit_number'))
        hit_totals = list(hit_totals)
        if len(targets) == 1 and move.get('hit_number', 1) == 1:
          hit_log = str(hit_rolls[0])
        else:
          hit_log = self.ui.replace_brackets(str(list(iterbatch(hit_rolls, move.get('hit_number')))))
        hit_count = (
          str(len(targets) * move.get('hit_number', 1))
          if 1 in (len(targets), move.get('hit_number', 1))
          else f"{len(targets)}*{move.get('hit_number', 1)}"
        )
        hit_log = ','.join(
          f"{target.get_evade()} ({target.get_sh()})" for target in targets
        ) + f"\n{hit_count}d100->{hit_log} + "
        hit_log = f"{ptcp.get_sh()} Attack Rolls:\nEvasion DC: {hit_log}"
        hit_log += str(hit_stat)
        hit_log += (
          " + " + ' + '.join(f"{bonus[0]} ({bonus[1]})") for bonus in hit_bonuses
        ) if hit_bonuses else ""
        if len(hit_totals) > 1:
          hit_log += f" = {hit_totals}"
        else:
          hit_log += " = " + str(hit_totals[0])
        for target, hit_totals_target in iterzip(targets, hit_totals):
          if type(hit_totals_target) == int:
            hit_totals_target = [hit_totals_target]
          for hit_total in hit_totals_target:
            hit_margin = hit_total - target.get_evade()
            if hit_margin < 0:
              hit_bank["miss"].append(target)
              hit_bank_reverse[target].append("miss")
            elif 'autocrit' in move['effects'] or hit_margin >= target.get_crit_thresh(move, ptcp, self):
              # todo: account for passive effects that change crit_threshold
              hit_bank["crit"].append(target)
              hit_bank_reverse[target].append("crit")
            elif hit_margin >= 0:
              hit_bank["hit"].append(target)
              hit_bank_reverse[target].append("hit")
            else:
              raise ValueError(f"Hit_margin {hit_margin} does not qualify for miss, crit, or hit!")
        if len(targets) == 1 == move.get('hit_number', 1):
          hit_summary = f'. {"Hit." if hit_bank["hit"] else "Crit!" if hit_bank["crit"] else "Miss."}'
        else:
          hit_summary = f". "
          for key, value in hit_bank.items():
            if value:
              hit_summary += f"{len(value)} {key}, "
          hit_summary = hit_summary[:-2] + '.'
        self.log(self.ui.replace_brackets(hit_log) + hit_summary + '\n')
      else:
        self.log(f"{ptcp.get_sh()} Attack Roll: auto-hit.\n")
        for target in targets:
          if 'autocrit' in move['effects'] or target.get_crit_thresh(move, ptcp, self) <= 0:
            hit_bank["crit"].append(target)
            hit_bank_reverse[target].append("crit")
          else:
            hit_bank["hit"].append(target)
            hit_bank_reverse[target].append("hit")
      
      def deal_damage(targets, hit_type_list):
        # assert len(targets) == 1 or len(hit_type_list) == 1
        # for now deal_damage is used with the above condition in effect, because the logging would look messy otherwise, but it's still implemented to be able to take more than one item on both lists
        
        if [] in (targets, hit_type_list):
          return
        
        def weapon_roll(weapon):
          wap = weapon["attack_power"]
          if len(wap) == 1:
            return wap[0]
          else:
            return sum(rolldie(wap[0], wap[-1]))
          
        damage_stat = ptcp.stats['melee'] if "melee" in move["attack_type"] else ptcp.stats['arts']
        defence_stat = "defence" if "melee" in move["attack_type"] else "resistance"
        damage_bonuses = []; damage_count = 0
        damage_rolls_list = []; damage_totals_list = []
        exemptions = set(); mult_list_list = []
        # print(hit_bank, hit_bank_reverse, targets, hit_type_list)
        for hit_types, target in iterzip(hit_type_list, targets):
          if type(hit_types) != list:
            hit_types = [hit_types]
          damage_rolls = []; damage_totals = []; mult_list = []
          for hit_type in hit_types:
            if hit_type == "miss":
              continue
            damage_count += 1
            damage_roll = weapon_roll(ptcp.main_weapon)
            mult = 1
            if hit_type == "crit":
              mult *= 2
            # todo: work in bonuses and maluses that are multiplicative, not just additive
            # only crits and multipliers that may vary per hit, like elemental weaknesses, get rolled up into the "mult"" argument, though
            damage_total = max(0, sum([damage_roll, damage_stat * move.get('attack_multiplier', 1)] + damage_bonuses) * mult - target.stats[defence_stat])
            damage_rolls.append(damage_roll); damage_totals.append(damage_total)
            mult_list.append(mult)
          if len(damage_rolls) < 1:
            exemptions.add(target)
          elif len(damage_rolls) == 1:
            damage_rolls_list.append(damage_rolls[0]); damage_totals_list.append(damage_totals[0])
            mult_list_list.append(mult_list[0])
          else:
            damage_rolls_list.append(damage_rolls); damage_totals_list.append(damage_totals)
            mult_list_list.append(mult_list)
        if set(targets) - exemptions == set():
          return
        elif len(targets) == 1:
          damage_rolls_list = damage_rolls_list[0]
          damage_totals_list = damage_totals_list[0]
          mult_list_list = mult_list_list[0]
        damage_log = ""
        if len(ptcp.main_weapon["attack_power"]) == 1:
          damage_log += f"{ptcp.main_weapon['attack_power']}" + (f" + {damage_stat}" if damage_stat > 0 else "")
        else:
          b, c = (
            ptcp.main_weapon["attack_power"][0],
            ptcp.main_weapon["attack_power"][-1],
          )
          if damage_count != 1:
            damage_log += "{damage_count}*"
          damage_log += f"{b}d{c}->{damage_rolls_list}"
        if damage_stat: # some weapons like guns only do weapon damage, no user stats
          damage_log += f" + {damage_stat}"
          damage_log += f"*{move.get('attack_multiplier')}" if move.get("attack_multiplier", 1) != 1 else ""
        damage_log += (
          " + " + ' + '.join(f"{bonus[0]} ({bonus[1]})") for bonus in damage_bonuses
        ) if damage_bonuses else ""
        crits_re = re.compile(r"[^\[\], 1]")
        if crits_re.search(str(mult_list_list)):
          damage_log = f"({damage_log}) * {mult_list_list}"
        inter_total = ""
        if len(targets) == 1: # not folded into next condition to exclude len 1 targets cases from elif cond
          if type(damage_totals_list) == list:
            inter_total = " = " + '+'.join(str(total) for total in damage_totals_list)
            damage_totals_list = sum(damage_totals_list)
        elif max(len(totals) if type(totals) == list else 1 for totals in damage_totals_list) > 1:
          inter_total = " = " + str(list('+'.join(str(total) for total in totals) if type(totals) == list else totals for totals in damage_totals_list))
          damage_totals_list = list(sum(totals) if type(totals) == list else totals for totals in damage_totals_list)
        if len(targets) > 1:
          damage_log += f" - {list(target.stats[defence_stat] for target in targets if not target in exemptions)}"
        else:
          damage_log += f" - {targets[0].stats[defence_stat]}"
        damage_log += f"{inter_total} = {damage_totals_list}"
        
        damage_log = f"{ptcp.get_sh()} Damage Rolls:\nEnemy HP: " + ','.join(
          f"{target.stats['currhp']} ({target.get_sh()})" for target in targets if not target in exemptions
        ) + '\n' + damage_log
        
        if type(damage_totals_list) != list:
          damage_totals_list = [damage_totals_list]
        for damage_total, target in iterzip(damage_totals_list, targets):
          target.stats["currhp"] = max(0, target.stats["currhp"] - damage_total)
        damage_log += f"\nRemaining HP: {list(target.stats['currhp'] for target in targets if not target in exemptions)[0 if len(targets) == 1 else None]}\n"
        self.log(self.ui.replace_brackets(damage_log))
        
        for func in ptcp.onhit:
          func(ptcp, targets, hit_types_list)
        
        # if hit_type == "crit":
          # ptcp.addpoints('cp', 5)
        # else:
          # ptcp.addpoints('cp', 1)
        
        for target, hit_types in iterzip(targets, hit_type_list):
          if not target.is_koed():
            for func in target.onstruck:
              func(target, ptcp, hit_types)
      
      if move.get('hit_number', 1) > 1:
        for target in targets:
          deal_damage([target], hit_bank_reverse[target])
      else:
        for hit_type in ("hit", "crit", "miss"):
          deal_damage(hit_bank[hit_type], [hit_type] * len(hit_bank[hit_type]))
