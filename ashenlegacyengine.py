#!/usr/bin/env python3
import battle, core
from ui import UI

commands = [
  'check',
  'diceroll',
  'updatestat',
]

def main():
  
  metadata = core.load_state('config.sav')
  verbose = True
  if not metadata:
    metadata = core.init_metadata()
  with UI(metadata) as ui:
    n = ui.log("Welcome to the dice and battle simulator built for Ashen Legacy.")
  
    save_state = core.load_state(f"autosave{ui.last_autosave}.sav") if ui.last_autosave > 0 else {}
    # if verbose:
    #   ui.log(f'Current save state: {save_state}\nLast autosave: {ui.last_autosave}')
    if not save_state:
      save_state = core.new_save_state()
      ui.log('Created new save state.')
      core.autosave(save_state, ui)
    database = core.load_databases(save_state['databases'], ui)
    
    main_menu = ui.generate_menu("main")
    main_menu.opts.sanity_check = (core.sanity_check, [])
    main_menu.opts.battle_menu = (battle.Battle(ui, database, save_state).setup_screen2, [])
    main_menu.disable("sanity_check")
    main_menu._run_menu()

if __name__ == '__main__':
    main()
