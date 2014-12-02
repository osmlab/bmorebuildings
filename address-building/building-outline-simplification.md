# Building Outline Simplification


## Import Data into Database

Create Postgres database named `buildings`.

```sql
-- Add PostGIS extensions
create extension postgis;
```

Import buildings Shapefile and add `cleanGeometry.sql` function.

```bash
shp2pgsql -s 2248 building.shp buildings | psql -d buildings
psql -d buildings < cleanGeometry.sql
```


## Simplify Outlines while Preserving Topology

Based on http://trac.osgeo.org/postgis/wiki/UsersWikiSimplifyPreserveTopology.

```sql
-- Extract multipolygons into polygons
create table poly as (
    select gid, (st_dump(geom)).*
    from buildings
);
create index poly_geom_gist on poly using GIST(geom);

-- Extract rings out of polygons
create table rings as (
    select st_exteriorRing((st_dumpRings(geom)).geom) as geom
    from poly
);
create index rings_geom_gist on rings using GIST(geom);

-- Simplify rings (takes a long time)
create table simplerings as (
    select st_simplifyPreserveTopology(st_linemerge(st_union(geom)), 0.000001) as geom
    from rings
);
create index simplerings_geom_gist on simplerings using GIST(geom);

-- Extract lines from simplified rings
create table simplelines as (
    select (st_dump(geom)).geom as geom
    from simplerings
);
create index simplelines_geom_gist on simplelines using GIST(geom);

-- Rebuild polygons from lines (takes a long time)
create table simplepolys as (
    select (st_dump(st_polygonize(distinct geom))).geom as geom
    from simplelines
);
alter table simplepolys add column gid serial primary key;
create index simplepolys_geom_gist on simplepolys using gist(geom);

-- Clean building geometry
create table simple_buildings as (SELECT cleangeometry(geom) as geom FROM simplepolys);

-- Remove interior courtyards (takes a long time)
create table bunion as (select (ST_Dump(ST_Union(ST_MakeValid(geom)))).* as geom from poly);
delete from simple_buildings where not exists (
    select * from bunion
    where st_intersects(bunion.geom, simple_buildings.geom)
    and st_area(st_intersection(bunion.geom, simple_buildings.geom))/st_area(simple_buildings.geom) > 0.5
);
```
