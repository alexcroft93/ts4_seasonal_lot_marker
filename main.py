import services
import sims4.commands
from objects.system import create_object
from sims4.math import Location, Transform
from routing import SurfaceIdentifier, SurfaceType
from seasons.seasons_enums import SeasonType, SeasonSetSource

# Global dictionary: season -> list of saved objects
seasonal_snapshots = {
    "spring": [],
    "summer": [],
    "fall": [],
    "winter": []
}

# --- Utility: get objects in the current lot ---
def get_lot_objects():
    """Returns all non-Sim objects in the ObjectManager."""
    obj_mgr = services.object_manager()
    objs = []
    for o in obj_mgr.get_all():
        if o.is_sim or o.definition is None:
            continue
        objs.append(o)
    return objs

# --- Save season snapshot ---
@sims4.commands.Command('seasonal.snapshot_save', command_type=sims4.commands.CommandType.Live)
def snapshot_save(season: str=None, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    if season not in seasonal_snapshots:
        output(f"Invalid season. Use: {list(seasonal_snapshots.keys())}")
        return

    objs = get_lot_objects()
    seasonal_snapshots[season] = []

    for obj in objs:
        data = {
            "definition_id": obj.definition.id,
            "position": obj.position,
            "orientation": obj.orientation,
            "level": obj.level
        }
        seasonal_snapshots[season].append(data)

    output(f"Saved {len(seasonal_snapshots[season])} objects for {season}.")

# --- Clear objects in the current lot ---
def clear_lot_objects():
    """Clears all objects in the current lot (except Sims)."""
    for obj in list(services.object_manager().get_all()):
        if obj.is_sim:
            continue
        try:
            obj.destroy(source=obj, cause="Seasonal snapshot switch")
        except:
            pass

# --- Load season snapshot ---
@sims4.commands.Command('seasonal.snapshot_load', command_type=sims4.commands.CommandType.Live)
def snapshot_load(season: str=None, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    if season not in seasonal_snapshots:
        output(f"Invalid season. Use: {list(seasonal_snapshots.keys())}")
        return

    data_list = seasonal_snapshots[season]
    if not data_list:
        output(f"No snapshot saved for {season}.")
        return

    clear_lot_objects()

    def_mgr = services.definition_manager()
    zone_id = services.current_zone_id()
    count = 0

    for data in data_list:
        definition = def_mgr.get(data["definition_id"])
        if definition is None:
            continue

        try:
            new_obj = create_object(definition, obj_id=0)
            if new_obj is None:
                continue

            transform = Transform(data["position"], data["orientation"])
            routing_surface = SurfaceIdentifier(zone_id, data["level"], SurfaceType.SURFACETYPE_WORLD)
            location = Location(transform, routing_surface)

            new_obj.location = location
            count += 1
        except Exception as e:
            output(f"Error spawning: {e}")

    output(f"Loaded {count} objects for {season}.")

# --- Map enum (game) -> snapshot ITA ---
SEASON_MAP = {
    SeasonType.SUMMER: "summer",
    SeasonType.FALL: "fall",
    SeasonType.WINTER: "winter",
    SeasonType.SPRING: "spring",
}

# --- Cheat: change season + apply snapshot ---
@sims4.commands.Command('seasonal.set_season', command_type=sims4.commands.CommandType.Cheat)
def seasonal_set_season(season: SeasonType=None, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    if season is None:
        output("You must specify a season: 0=Summer, 1=Fall, 2=Winter, 3=Spring")
        return

    season_service = services.season_service()
    if season_service is None:
        output("SeasonService not available.")
        return

    # Change the season in the game (only in Live mode!)
    season_service.reset_region_season_params()
    season_service.set_season(season, SeasonSetSource.CHEAT)
    services.weather_service().reset_forecasts()

    # Link to our map
    snapshot_name = SEASON_MAP.get(season)
    if snapshot_name in seasonal_snapshots:
        snapshot_load(snapshot_name, _connection=_connection)
        output(f"Season changed to {snapshot_name} + objects loaded.")
    else:
        output(f"Season changed to {snapshot_name}, but no snapshot found.")
