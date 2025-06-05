import json, math, os, random, sys

error_reference = {
  "Expecting property name enclosed in double quotes" : "JSON dicts don't accept a comma after last entry unlike Python."
}

def rolldie(a=1, d=100, bank=None):
  """Returns the results of 'a' number of rolls of a 'd'-sided die as a list.
  
  If a record of unused rolls from a dice with the same number of sides exists
  in 'bank', the results are sourced from there first before new numbers are
  generated."""
  
  bank = bank or dict()
  if not d in bank:
    bank[d] = {'index': 0, 'rolled': []}
  overflow = len(bank[d]['rolled']) - bank[d]['index']
  for n in range(a - overflow):
    bank[d]['rolled'].append(random.randint(1, d))
  bank[d]['index'] += a
  
  return bank[d]['rolled'][bank[d]['index'] - a:bank[d]['index']]
# note to self: could this get reworked to replace return with yield?
# Would having to append newly generated rolls to the list get in the way of that?

def load_state(savepath):
  state = dict()
  if not savepath.startswith('saves'):
    savepath = os.path.join('saves', savepath)
  if os.path.isfile(savepath):
    with open(savepath, 'rb') as f:
      state = json.load(f)
  else:
    print("cannot find", savepath)
  return state

def save_state(state, savepath):
  if not savepath.startswith('saves'):
    savepath = os.path.join('saves', savepath)
  os.makedirs(os.path.dirname(savepath), exist_ok=True)
  with open(savepath, 'w') as f:
    mute = json.dump(state, f, indent=4)

def autosave(state, ui):
  ui.last_autosave = (ui.last_autosave % 20) + 1
  save_state(state, f"autosave{ui.last_autosave}.sav")
  save_state(ui.metadata(), "config.sav")

def new_save_state():
  return {
    'databases': {'character': ['monster', 'sample']},
    'battle': {'participants': dict(), 'field_conds': dict()},
    'past_dice': dict(),
    'past_input': list(),
  }

def init_metadata():
  return {'width': 40, 'last_autosave': 0, 'logfilename': 'log.txt'}

def load_databases(metadata, ui):
  database = dict()
  for fname in os.listdir('masters'):
    if not fname.startswith('database-'):
      continue
    key = fname.split('.')[0][9:].split('-', 1)
    if len(key) > 1 and key[0] in metadata and not key[1] in metadata[key[0]]:
      continue
    with open('masters/' + fname, 'rb') as f:
      try:
        imported_data = json.load(f)
        print(f"Loaded database {'-'.join(key)}.")
        if len(key) > 1:
          for entry in imported_data:
            imported_data[entry]['subkey'] = key[1]
        if not key[0] in database:
          database[key[0]] = imported_data
        else:
          collisions = set(database[key[0]]).intersection(set(imported_data))
          for entry in collisions:
            choice = ui.selection(
              f"Entry {entry} from {'-'.join(key)} already in database/{key[0]}!"
              + "\nChoose 1: skip, or 2: overwrite", domain=('1','2')
            )
            if choice == '1':
              del imported_data[entry]
            else:
              assert choice == '2', "Should only be two choices here..."
          database[key[0]] |= imported_data
      except Exception as e:
        print(f"Master data for database {'-'.join(key)} could not be loaded!")
        msg = repr(e); print('-' + msg)
        cross_ref = filter(lambda x: x in msg, error_reference)
        if cross_ref:
          for entry in cross_ref:
            print('-Hint:', error_reference[entry])
  
  if not database:
    print("No databases loaded!")
  
  print()
  
  return database

def deal_effects(effects):
  for key, item in effects:
    pass

def sanity_check(ui):
  faces = int(ui.selection(
    "Pick number from 2 to 100", domain=tuple(str(n) for n in range(2, 101))
  ))
  res = dict()
  for n in range(1, faces + 1):
    res[n] = 0
  bank = dict()
  for _ in range(faces * 1000):
    res[sum(rolldie(1, d=faces, bank=bank))] += 1
  
  paged_dict = {1: []}; page = 1
  for key, value in res.items():
    if key > (page * 20):
      page += 1; paged_dict[page] = []
    paged_dict[page].append(
      f"{key: >3}: {('x'*round(value/50)).replace('xxxxx', 'xxxxx ').strip()}"
      +f" ({value})"
    )
  
  print(
    f"Result of rolling 1d{faces} {faces * 1000} times,"
    +" each x representing count of 50:"
  )
  
  ui.print_tabs(paged_dict)
  ui.delete_last_line()
