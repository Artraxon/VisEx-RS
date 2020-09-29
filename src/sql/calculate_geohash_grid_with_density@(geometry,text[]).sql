create function calculate_geohash_grid_with_density(boundary geometry, ignoredsources text[])
    returns TABLE(geohash text, hasharea geometry, timestmp timestamp with time zone, forlabel text, totalarea double precision, covered double precision)
    language sql
as
$$
WITH extended as (
    WITH foundAreas as
             (SELECT DISTINCT patches.acquisition as aq, patches.area as geom
              FROM patches
                       JOIN tile_sources
                            ON patches.part_of = tile_sources.tile_source
              WHERE NOT part_of = ANY(ignoredSources) AND
                    st_intersects(boundary, tile_sources.area)),
         crossed as
             (SELECT timestamps.timestmp, foundAreas.geom as area
              FROM (SELECT DISTINCT ON (foundAreas.aq) foundAreas.aq as timestmp FROM foundAreas ORDER BY foundAreas.aq) as timestamps,
                   foundAreas),
         foundlabels as
             (SELECT labels.area, labels.acquisition, array_agg(labels.label) as agglabels
              FROM labels
                       JOIN foundAreas ON labels.area = foundAreas.geom AND labels.acquisition = foundAreas.aq
              GROUP BY labels.area, labels.acquisition)
    --extended Query
    SELECT DISTINCT crossed.timestmp, crossed.area, foundLabels.agglabels
    FROM crossed
             LEFT OUTER JOIN foundLabels
                 ON crossed.area = foundLabels.area AND crossed.timestmp = foundLabels.acquisition ),
     --outer with statements
     monthly as (
         --group by month
         SELECT
             date_trunc('month', backwards.timestmp) as truncatedTime,
             backwards.area,
             array_agg(DISTINCT u.label) as carryforward_labels,
             MIN(carryforward_timestamp) as carryforward_timestamp
         FROM (
             --Last Observation carried forward but inverse, so that leading nulls are filled up
                  select q.timestmp, q.area, first_value(q.carryforward_labels)over w as carryforward_labels, first_value(q.timestmp) over w as carryforward_timestamp
                  from (
                           select *, sum(case when carryforward_labels is null then 0 else 1 end) over (partition by forwarded.area order by forwarded.timestmp DESC) as value_partition
                           from (
                               --Last Observation Carried Forward (for future values)
                                    select q.timestmp, q.area, first_value(q.agglabels)over w as carryforward_labels, first_value(q.timestmp) over w as carryforward_timestamp
                                    from (
                                             select *, sum(case when agglabels is null then 0 else 1 end) over (partition by extended.area order by extended.timestmp ) as value_partition
                                             from extended
                                         ) as q
                                        window w as (partition by q.area, value_partition order by q.timestmp)) as forwarded)
                           as q
                      window w as (partition by q.area, value_partition order by q.timestmp DESC )) as backwards
                  CROSS JOIN LATERAL unnest(backwards.carryforward_labels) as u(label)
         GROUP BY truncatedTime, backwards.area
     ),
     foundHashs as (
         SELECT *
         FROM hashtiles,
              (select st_union(ts.area) as outline from tile_sources ts where st_intersects(ts.area, boundary) group by true) as outlineHashes
         WHERE st_intersects(outlineHashes.outline, hashtiles.area)),
     combined as (
         SELECT
         monthly.truncatedTime                          as timestmp,
         monthly.area                                   as tileArea,
         carryforward_labels,
         carryforward_timestamp,
         foundHashs.area                                as hashArea,
         foundHashs.geohash,
         st_intersection(foundHashs.area, monthly.area) as bounded
         FROM monthly JOIN foundHashs ON st_intersects(monthly.area, foundHashs.area)),
     withTotals as (
         SELECT combined.timestmp,
                combined.hashArea,
                combined.carryforward_labels,
                combined.carryforward_timestamp,
                combined.geohash,
                combined.bounded,
                combined.tileArea,
                --calculates the total area that was covered at each step as a running sum
                st_union( bounded) over w as total
         FROM combined
         --GROUP BY forEachLabel.geohash, forEachLabel.timestmp, forEachLabel.computing, time_distance(forEachLabel.timestmp, forEachLabel.carryforward_timestamp)
             WINDOW w as (
                 PARTITION BY combined.geohash,
                     combined.timestmp
                 --the combined.bounded is very important because it gives a total order. We need the same order at every step!
                 ORDER BY time_distance(combined.timestmp, combined.carryforward_timestamp), combined.bounded)
         ),
     forEachLabel as (
         --Extends every row over their carried labels
         SELECT * FROM withTotals m
                           CROSS JOIN LATERAL unnest(carryforward_labels) as l(singleLabel)),
     spreadLabelSet as (
         SELECT * FROM
             (SELECT DISTINCT ON (geohash, timestmp, bounded)
                  timestmp, geohash, hashArea, carryforward_labels, carryforward_timestamp, bounded, tileArea, total, labelsAgg
              FROM forEachLabel JOIN
                  --Sums up all the distinct labels that occur in an hasharea ever
                   (SELECT geohash, array_agg(DISTINCT forEachLabel.singleLabel) as labelsAgg FROM forEachLabel
                    GROUP BY forEachLabel.geohash) as allLabels
                  USING (geohash)) as labelSet
                 -- And then extends this "label set" over all entries for an geohash again.
                 -- Against this label the matched area will be calculated
                 CROSS JOIN LATERAL unnest(labelsAgg) as l(computing)
     ),
     foundFirsts as (
         --calculates the area of the summed up matched area
         SELECT geohash, hashArea, timestmp, summedUp.computing, MAX(summedUp.totalArea) as totalArea, MAX(summedUp.matchedArea) as matchedArea FROM
             (SELECT *,
                     st_area(withMatched.total::geography) as totalArea,
                     st_area(withMatched.matched::geography) as matchedArea
              FROM
                  (SELECT *,
                          --sums up the matched area
                          st_union(diffedAtCarried.diff) over w as matched
                   FROM
                       (SELECT *,
                               --calculates what geometry would be added if this patch contains the computing label
                               CASE WHEN spreadLabelSet.computing = ANY(spreadLabelSet.carryforward_labels)
                                        THEN st_difference(spreadLabelSet.bounded, lag(total, 1, st_geomfromtext('POLYGON EMPTY', 4326)) over w)
                                    ELSE st_geomfromtext('POLYGON EMPTY', 4326) END as diff
                        FROM spreadLabelSet
                            WINDOW w as (
                                PARTITION BY spreadLabelSet.geohash,
                                    spreadLabelSet.timestmp,
                                    spreadLabelSet.computing
                                ORDER BY time_distance(spreadLabelSet.timestmp, spreadLabelSet.carryforward_timestamp), spreadLabelSet.bounded)
                       ) as diffedAtCarried
                       WINDOW w as (
                           PARTITION BY diffedAtCarried.geohash,
                               diffedAtCarried.timestmp,
                               diffedAtCarried.computing
                           ORDER BY time_distance(diffedAtCarried.timestmp, diffedAtCarried.carryforward_timestamp), diffedAtCarried.bounded)
                  ) as withMatched
             ) as summedUp
         GROUP BY summedUp.hashArea, summedUp.geohash, summedUp.timestmp, summedUp.computing
         ORDER BY summedUp.geohash, summedUp.computing, summedUp.timestmp)
SELECT * from foundFirsts
ORDER BY geohash, computing, timestmp;
$$;

alter function calculate_geohash_grid_with_density(geometry, text[]) owner to postgres;

