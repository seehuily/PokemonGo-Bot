import json
import os

from pokemongo_bot.base_task import BaseTask
from pokemongo_bot.cell_workers.pokemon_catch_worker import PokemonCatchWorker
from utils import distance
from pokemongo_bot.worker_result import WorkerResult
from pokemongo_bot.base_dir import _base_dir


class CatchVisiblePokemon(BaseTask):
    SUPPORTED_TASK_API_VERSION = 1

    def work(self):
        num_catchable_pokemon = 0
        if 'catchable_pokemons' in self.bot.cell:
            num_catchable_pokemon = len(self.bot.cell['catchable_pokemons'])

        num_wild_pokemon = 0
        if 'wild_pokemons' in self.bot.cell:
            num_wild_pokemon = len(self.bot.cell['wild_pokemons'])

        num_available_pokemon = num_catchable_pokemon + num_wild_pokemon

        if num_catchable_pokemon > 0:
            # Sort all by distance from current pos- eventually this should
            # build graph & A* it
            self.bot.cell['catchable_pokemons'].sort(
                key=
                lambda x: distance(self.bot.position[0], self.bot.position[1], x['latitude'], x['longitude'])
            )
            for pokemon in self.bot.cell['catchable_pokemons']:
                #user_web_catchable = os.path.join(_base_dir, 'web', 'catchable-{}.json'.format(self.bot.config.username))
                #with open(user_web_catchable, 'w') as outfile:
                #json.dump(pokemon, outfile)
                self.emit_event(
                    'catchable_pokemon',
					formatted='Something rustles nearby: {pokemon_id} SPID {spawn_point_id} {encounter_id}POS ({latitude}, {longitude}{expiration_timestamp_ms})',
                    data={
                        'pokemon_id': self.bot.pokemon_list[pokemon['pokemon_id'] - 1]['Name'],
                        'spawn_point_id': pokemon['spawn_point_id'],
                        'encounter_id': '',
                        'latitude': pokemon['latitude'],
                        'longitude': pokemon['longitude'],
                        'expiration_timestamp_ms': '',
                    }
                )

            while num_catchable_pokemon > 0:
                num_catchable_pokemon -= 1
                rv = self.catch_pokemon(self.bot.cell['catchable_pokemons'].pop(0))
                if rv == WorkerResult.SUCCESS and num_catchable_pokemon > 0 :
                    return WorkerResult.RUNNING

            return WorkerResult.SUCCESS

        if num_wild_pokemon > 0:
            # Sort all by distance from current pos- eventually this should
            # build graph & A* it
            self.bot.cell['wild_pokemons'].sort(
                key=
                lambda x: distance(self.bot.position[0], self.bot.position[1], x['latitude'], x['longitude']))
            self.catch_pokemon(self.bot.cell['wild_pokemons'].pop(0))

            if num_wild_pokemon > 1:
                return WorkerResult.RUNNING
            else:
                return WorkerResult.SUCCESS

    def catch_pokemon(self, pokemon):
        worker = PokemonCatchWorker(pokemon, self.bot, self.config)
        return_value = worker.work()

        return return_value
