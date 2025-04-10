
class Participant():
  
  def __init__(self, name, team, jsondata, currvalues=dict()):
    # basedata is the "master data" which determines "default" values,
    # and should not be changed unless it is to do so permanently
    self.basedata = jsondata['character'][name]
    self.equipdata = jsondata['equipment']
    # todo: load all equipment, designate currently equipped weapons
    self.refname = name
    self.team = team # assume 1 as controlled team
    
    # setting curr values...
    self.stats = self.basedata['stats'] | currvalues
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
    
    self.main_weapon = self.set_main_weapon()
    self.equipment = dict() | self.basedata.get('equipment', {})
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
    self.basic_attack = {
      'movename': "Basic Attack",
      'default_target': ('enemy', 'single'),
      # 'attack_type': self.main_weapon['attack_type'],
      'attack_multiplier': 1,
      'effects': {
      }
    }
    self.moves = {'basic_attack': self.basic_attack} | self.basedata.get('moves', dict())
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
    self.counters = dict()
  
  def __repr__(self):
    return f"<Ptcp {self.get_sh()}:{self.refname}>"
  
  def set_main_weapon(self):
    self.main_weapon = self.basedata.get('main_weapon', '') or 'bare_hands'
    self.main_weapon = self.basedata.get('equipment', self.equipdata).get(
      self.main_weapon
    )
    if not self.main_weapon:
      print(f'Failed to equip main weapon {self.main_weapon}, defaulting to bare hands.')
      self.main_weapon = {
        "fullname": "Bare Hands",
        "attack_type": ["melee", "physical"],
        "weaponstat": [1],
        "weaponeffect": "",
      }
  
  def effectiveevade(self):
    return self.stats['speed'] + sum(item[0] for key, item in self.statmods['evade'])
  
  def get_sh(self):
    shorthand = self.basedata.get('shorthand')
    shorthand = shorthand or self.refname if len(self.refname) < 8 else ''
    shorthand = shorthand or "".join(
      name[0] for name in self.basedata['fullname'].split()
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
    ptcpdict = vars(self)
    del ptcpdict["basedata"]
    del ptcpdict["equipdata"]
    
    return ptcpdict
