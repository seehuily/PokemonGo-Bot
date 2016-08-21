# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from random import random, uniform
from math import asin, atan, cos, exp, log, pi, sin, sqrt, tan
from pokemongo_bot import inventory
from pokemongo_bot.constants import Constants
from pokemongo_bot.walkers.walker_factory import walker_factory
from pokemongo_bot.worker_result import WorkerResult
from pokemongo_bot.base_task import BaseTask
from utils import distance, format_dist, fort_details


class MoveToFort(BaseTask):
    SUPPORTED_TASK_API_VERSION = 1

    def initialize(self):
        self.lure_distance = 0
        self.lure_attraction = self.config.get("lure_attraction", True)
        self.lure_max_distance = self.config.get("lure_max_distance", 2000)
        self.ignore_item_count = self.config.get("ignore_item_count", False)
        self.walker = self.config.get('walker', 'StepWalker')
        self.bot_zone = self.config.get("bot_zone", False)
        self.zone_radius = self.config.get("zone_radius", 1000)
        self.recent_dest_fort = None
        self.recent_dest_fortname = 'Unknown'

    def should_run(self):
        has_space_for_loot = inventory.Items.has_space_for_loot()
        if not has_space_for_loot and not self.ignore_item_count:
            self.emit_event(
                'inventory_full',
                formatted="Inventory is full. You might want to change your config to recycle more items if this message appears consistently."
            )
        return has_space_for_loot or self.ignore_item_count or self.bot.softban

    def is_attracted(self):
        return (self.lure_distance > 0)

    def work(self):
        if not self.should_run():
            return WorkerResult.SUCCESS

        unit = self.bot.config.distance_unit  # Unit to use when printing formatted distance

        if self.recent_dest_fort:
            nearest_fort = self.recent_dest_fort
            fort_name = self.recent_dest_fortname
        else:
            nearest_fort = self.get_nearest_fort()
            if nearest_fort is None:
                rlat, rlng = self._get_random_spot_in_zone(self.bot.start_position[0], self.bot.start_position[1], self.zone_radius)
                self.recent_dest_fort = {'latitude':rlat, 'longitude':rlng}
                self.recent_dest_fortname = 'Random Point'
                self.bot.recent_forts = self.bot.recent_forts[1:] + ['0']
                self.bot.update_recent_forts()
                return WorkerResult.RUNNING

        if self.recent_dest_fortname == 'Random Point':
            way_fort = self._get_nearest_fort_on_pos_way(self.recent_dest_fort['latitude'], self.recent_dest_fort['longitude'])
            if way_fort is not None:
                self.recent_dest_fort = way_fort
                self.recent_dest_fortname = 'Way Fort to RP'
                return WorkerResult.RUNNING

        lat = nearest_fort['latitude']
        lng = nearest_fort['longitude']

        self.bot.fort_position = lat,lng,0

        if self.recent_dest_fort is None:
            fortID = nearest_fort['id']
            details = fort_details(self.bot, fortID, lat, lng)
            fort_name = details.get('name', 'Unknown')
            self.recent_dest_fortname = fort_name
            self.recent_dest_fort = nearest_fort

        dist = distance(
            self.bot.position[0],
            self.bot.position[1],
            lat,
            lng
        )

        walk_speed = (self.bot.config.walk_max + self.bot.config.walk_min) / 2
        walk_time = dist / walk_speed
        rm_hur = int(walk_time / 3600)
        rm_mnt = int(walk_time % 3600 / 60)
        rm_sec = int(walk_time % 60)

        dist_msg = format_dist(dist, unit)
        time_msg = ')'
        if (rm_sec > 0):
            time_msg = '{}s'.format(rm_sec) + time_msg
        if (rm_mnt > 0):
            time_msg = '{}m'.format(rm_mnt) + time_msg
        if (rm_hur > 0):
            time_msg = '{}h'.format(rm_hur) + time_msg
        dist_msg = dist_msg + ' (' + time_msg

        if dist > Constants.MAX_DISTANCE_FORT_IS_REACHABLE:
            fort_event_data = {
                'fort_name': u"{}".format(fort_name),
                'distance': dist_msg,
            }

            if self.is_attracted() > 0:
                fort_event_data.update(lure_distance=format_dist(self.lure_distance, unit))
                self.emit_event(
                    'moving_to_lured_fort',
                    formatted="Moving towards pokestop ({fort_name}) - {distance} (attraction of lure {lure_distance})",
                    data=fort_event_data
                )
            else:
                self.emit_event(
                    'moving_to_fort',
                    formatted="Moving towards pokestop ({fort_name}) - {distance}",
                    data=fort_event_data
                )

            step_walker = walker_factory(self.walker,
                self.bot,
                lat,
                lng
            )

            if not step_walker.step():
                return WorkerResult.RUNNING

        self.emit_event(
            'arrived_at_fort',
            formatted='Arrived at fort (point).'
        )
        if self.recent_dest_fort:
            self.recent_dest_fort = None
            self.recent_dest_fortname = 'Unknown'

        return WorkerResult.SUCCESS

    def _print_fort(self, fort, sequ):
        lat = fort['latitude']
        lng = fort['longitude']
        fortID = fort['id']
        dist = distance(
            self.bot.start_position[0],
            self.bot.start_position[1],
            lat,
            lng
        )

        format_str = '  -- {} Print fort '.format(sequ)
        format_str = format_str + '{fort_name} - {distance}.'
        self.emit_event(
            'moving_to_fort',
            formatted = format_str,
            data = {
                'fort_name': fortID,
                'distance': format_dist(dist, self.bot.config.distance_unit),
            }
        )

    def _print_forts(self, forts, sequ):
        for fort in forts:
            if fort is not None:
                self._print_fort(fort, sequ)

    def _remove_outzone_fort(self, forts):
        if not self.bot_zone:
            return forts

        # Remove out of range forts
        forts = filter(lambda x: True if distance(
                        self.bot.start_position[0],
                        self.bot.start_position[1],
                        x['latitude'],
                        x['longitude']
                       ) < self.zone_radius else False, forts)
        return forts

    def _get_nearest_fort_on_lure_way(self, forts):

        if not self.lure_attraction:
            return None, 0

        lures = filter(lambda x: True if x.get('lure_info', None) != None else False, forts)

        if (len(lures)):
            dist_lure_me = distance(self.bot.position[0], self.bot.position[1],
                                    lures[0]['latitude'],lures[0]['longitude'])
        else:
            dist_lure_me = 0

        if dist_lure_me > 0 and dist_lure_me < self.lure_max_distance:

            self.lure_distance = dist_lure_me

            for fort in forts:
                dist_lure_fort = distance(
                    fort['latitude'],
                    fort['longitude'],
                    lures[0]['latitude'],
                    lures[0]['longitude'])
                dist_fort_me = distance(
                    fort['latitude'],
                    fort['longitude'],
                    self.bot.position[0],
                    self.bot.position[1])

                if dist_lure_fort < dist_lure_me and dist_lure_me > dist_fort_me:
                    return fort, dist_lure_me

                if dist_fort_me > dist_lure_me:
                    break

            return lures[0], dist_lure_me

        else:
            return None, 0

    def _get_nearest_fort_on_pos_way(self, pLat, pLng):

        forts = self.bot.get_forts(order_by_distance=True, distance_to_start_pos=True)
        # Remove all forts which were spun in the last ticks to avoid circles if set
        if self.bot.config.forts_avoid_circles:
            forts = filter(lambda x: x["id"] not in self.bot.recent_forts, forts)

        dist_sp_me = distance(self.bot.position[0], self.bot.position[1], pLat, pLng)

        for fort in forts:
            dist_sp_fort = distance(
                fort['latitude'],
                fort['longitude'],
                pLat,
                pLng)
            dist_fort_me = distance(
                fort['latitude'],
                fort['longitude'],
                self.bot.position[0],
                self.bot.position[1])

            if dist_sp_fort < dist_sp_me and dist_sp_me > dist_fort_me:
                return fort

        return None

    def _get_random_spot_in_zone(self, lat, lng, radius):
        radius_in_degree = 1.0 * radius / 111300
        u = random()
        v = random()
        w =  sqrt(u) * radius_in_degree
        t = 2 * pi * v

        xLat = w * cos(t) + lat
        yLng = w * sin(t) + lng

        return xLat, yLng

    def get_nearest_fort(self):

        forts = self.bot.get_forts(order_by_distance=True)
        # Remove out of zone forts
        forts = self._remove_outzone_fort(forts)

        # Remove stops that are still on timeout
        forts = filter(lambda x: x["id"] not in self.bot.fort_timeouts, forts)
        next_attracted_pts, lure_distance = self._get_nearest_fort_on_lure_way(forts)

        # Remove all forts which were spun in the last ticks to avoid circles if set
        if self.bot.config.forts_avoid_circles:
            forts = filter(lambda x: x["id"] not in self.bot.recent_forts, forts)

        self.lure_distance = lure_distance

        if (lure_distance > 0):
            return next_attracted_pts

        if len(forts) > 0:
            return forts[0]
        else:
            # All forts are out of range of start pos, retrieve the nearest
            # one to start position
            fort = self._get_nearest_fort_on_pos_way(self.bot.start_position[0], self.bot.start_position[1])
            if fort is not None:
                dis_to_start = distance(self.bot.start_position[0], self.bot.start_position[1], fort['latitude'], fort['longitude'])
                if dis_to_start < self.zone_radius:
                    return fort
            return None
