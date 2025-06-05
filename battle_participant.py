
class Participant():
  
  def __init__(self, name, team, btl_obj, currvalues=dict()):
    # basedata is the "master data" which determines "default" values,
    # and should not be changed unless it is to do so permanently
    self.basedata = btl_obj.DATABASE['character'][name]
    self.equipdata = btl_obj.DATABASE['equipment']
    # todo: load all equipment, designate currently equipped weapons
    self.refname = name
    self.team = team # assume 1 as controlled team
    
    self.stats = self.basedata['stats']
    self.equipment = self.basedata.get('equipment', {})
    self.onstart = dict()
    self.onturnstart = dict()
    self.beforehit = dict()
    self.onhit = dict()
    self.onstruck = dict()
    self.onturnend = dict()
    self.statmods = {
      'melee': dict(),
      'ranged': dict(),
      'hit': dict(),
      'speed': dict(),
      'evade': dict(),
      'defence': dict(),
      'arts': dict(),
      'casting': dict(),
      'resistance': dict(),
    }
    self.moves = {"basic_attack": {
      'movename': "Basic Attack",
      'default_target': ('enemy', 'single'),
      'attack_type': "melee",
      'attack_multiplier': 1,
      'effects': {
      }
    }}
    self.moves |= self.basedata.get('moves', dict())
    # Validate moves?
    # assert type(move.get('attack_multiplier')) == int and move.get('attack_multiplier', 0) > 0
    
    for equipment in self.equipment:
      pass
      # do self.statmods
    for quartz in self.basedata.get('quartz', {}):
      pass
      # do self.statmods and self.moves
    self.state = 'standby'
    self.attack_timing = 0
    # self.counters = dict() # use/turn counters can probably just go into the mods and timing-effect dicts instead?
    
    # setting curr values...
    for key, value in currvalues.items():
      # print(key, type(value))
      if type(value) == dict and hasattr(self, key):
        self2 = getattr(self, key, {})
        for key2, value2 in value.items(): # weapons and moves should only have 1 level of nesting, will need to edit this otherwise
          if type(value2) == dict and key2 in self2:
            self2[key2] = self2.get(key2, {}) | value2
          else:
            self2[key2] = value2
      else:
        setattr(self, key, value)
    if not 'currhp' in self.stats:
      default = self.basedata['stats']['defence'] * 10
      default += self.basedata['stats']['resistance'] * 5
      self.stats['currhp'] = self.stats.get('maxhp', default)
      # monster HP are set individually though
    if not 'currcp' in self.stats:
      self.stats['currcp'] = self.stats.get('maxcp', 200)
      # maxcp set-able just in case some don't have default 200
    if not 'currep' in self.stats:
      self.stats['currep'] = self.stats['maxep']
      # monsters don't have ARCUS
    
    self.set_main_weapon()
      
    action_menu = btl_obj.ui.generate_menu(f'{self.get_sh()} action', exit_word="pass", is_return=True)
    action_menu.opts.attack = (lambda x: x, [self.moves["basic_attack"]])
    action_menu.opts.crafts = (lambda: None, [])
    action_menu.opts.arts = (lambda: None, [])
    action_menu.opts.items = (lambda: None, [])
    action_menu.opts.break_turn = (lambda: None, [])
    self.action_menu = action_menu._run_menu
  
  def __repr__(self):
    return f"<Ptcp {self.get_sh()}:{self.refname}>"
  
  def set_main_weapon(self):
    refname = self.basedata.get("main_weapon", "") or "bare_hands"
    self.main_weapon = self.basedata.get("equipment", self.equipdata).get(refname)
    self.main_weapon["refname"] = refname
    if not self.main_weapon:
      print(f"Failed to equip main weapon {self.main_weapon}, defaulting to bare hands.")
      self.main_weapon = {
        "fullname": "Bare Hands",
        "refname": "bare_hands",
        "attack_type": ["melee", "physical"],
        "attack_power": [1],
        "weaponeffect": "",
      }
  
  def get_evade(self, mode="physical"):
    if mode == "physical":
      return self.stats['speed'] + sum(item[0] for key, item in self.statmods['evade'])
    elif mode =="arts":
      return 0
    else:
      raise ValueError('"mode" argument must be "physical"" or "arts"')
    
  def get_crit_thresh(self, move, atkr, btl_obj):
    crit_thresh = 100
    # check move effects
    # check atkr passives
    # check environment bonuses
    
    return crit_thresh
  
  def get_sh(self):
    shorthand = (
      getattr(self, "shorthand", self.basedata.get("shorthand")) or (
        self.refname.split('-')[0] if len(self.refname.split('-')[0]) < 8 else
        "".join(name[0] for name in self.basedata['fullname'].split())
      )
    )
    
    return shorthand
  
  def addpoints(self, pointtype, amount):
    assert pointtype in ('hp', 'cp', 'ep') and type(amount) == int, (pointtype, amount)
    self.stats['curr'+pointtype] = min(
      self.stats['max'+pointtype], self.stats['curr'+pointtype] + amount
    )
  
  def is_koed(self):
    if self.stats["currhp"] <= 0:
      return True
    else:
      return False
  
  def setstat(self, statname):
    self.stats[statname] = self.basedata[statname] # * multipliers and adders
  
  
  def desc_to_effect(self, effectname, line):
    if line.startswith('Each turn,'):
      pointer = self.onturnstart
    elif 'on hit' in line:
      pointer = self.onhit
    pointer[effectname] = None
  
  def effect_to_desc(self):
    pass

  def import_equip(self, equip):
    pass
  
  def todict(self):
    ptcpcopy = vars(self).copy()
    # deleting anything further nested than first level will need deepcopy, though
    del ptcpcopy["basedata"]
    del ptcpcopy["equipdata"]
    del ptcpcopy["action_menu"]
    ptcpcopy["main_weapon"] = self.main_weapon["refname"]
    
    return ptcpcopy
