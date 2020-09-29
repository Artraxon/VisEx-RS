CREATE FUNCTION get_timestamps_in_area(boundary text)
RETURNS TABLE(date timestamp with time zone)
language plpgsql
AS
$$
DECLARE
    bound geometry;
BEGIN
    bound = st_geomfromgeojson(boundary);
    SELECT acquisition FROM patches WHERE st_intersects(patches.area, bound)
    GROUP BY patches.acquisition;
end;
$$

CREATE FUNCTION find_absolute_by_time (boundary geometry, search text[]) returns TABLE(date timestamp with time zone, amount bigint)
language sql
AS
$$
SELECT geomatch.acquisition, count(*) FROM (SELECT area, acquisition FROM labels WHERE st_intersects(boundary, area) AND labels.label = ANY(search)
                                            GROUP BY area, acquisition) as geomatch
GROUP BY geomatch.acquisition
$$;

CREATE FUNCTION find_absolute_by_time_json(boundary text, search text[]) returns
TABLE(date timestamp with time zone, count bigint)
language sql
as
$$SELECT * FROM find_absolute_by_time(st_geomfromgeojson(boundary), search); $$