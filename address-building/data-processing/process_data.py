#!/usr/bin/python

# Data processing script for Baltimore City building and address import
# Matthew Petroff, January 2015
#
# This script is released into the public domain using the CC0 1.0 Public
# Domain Dedication: https://creativecommons.org/publicdomain/zero/1.0/
#
# Expects source data in source_data folder
#
# Expects a PostGIS database named "baltimore" to be accessible by the
# executing user: e.g. run the following as the postgres user
#   $ psql -c "create database baltimore"
#   $ psql -c "alter database baltimore owner to USERNAME"
#   $ psql -d baltimore -c "create extension postgis"
#
# Tested under Linux Mint 17.1

import os
import subprocess



#
# Import data and add cleanGeometry.sql function
#

print 'Importing data...'
os.system('shp2pgsql -s 2248 source_data/building.shp buildings | psql -d baltimore')
os.system('shp2pgsql -I -s 2248 source_data/AddressPoint_BaltCity.shp raw_addresses | psql -d baltimore')
os.system('osm2pgsql -d baltimore source_data/maryland-latest.osm.pbf')
p = subprocess.Popen('psql -d baltimore < cleanGeometry.sql', 
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
print p.communicate(input='\q')


#
# Simplify outlines while preserving topology
#

print 'Simplifying building outlines (takes a long time)...'
p = subprocess.Popen('psql -d baltimore', 
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
print p.communicate(input='''
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
    select st_simplifyPreserveTopology(st_linemerge(st_union(geom)), 0.001) as geom
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
create table simple_buildings as (select cleangeometry(geom) as geom from simplepolys);

-- Remove interior courtyards (takes a long time)
create table bunion as (select (ST_Dump(ST_Union(ST_MakeValid(geom)))).* as geom from poly);
delete from simple_buildings where not exists (
    select * from bunion
    where st_intersects(bunion.geom, simple_buildings.geom)
    and st_area(st_intersection(bunion.geom, simple_buildings.geom))/st_area(simple_buildings.geom) > 0.5
);

create index simple_buildings_geom_gist on simple_buildings using GIST(geom);

\q
''')



#
# Divide buildings into two categories, those intersecting with existing
# buildings and those not
#

print 'Finding intersecting buildings...'
p = subprocess.Popen('psql -d baltimore', 
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
print p.communicate(input='''
alter table simple_buildings add column id serial;
update simple_buildings set id = default;

create table non_intersecting_buildings as (
select 
  *
from 
  simple_buildings
where 
  not exists 
  (select * 
   from 
     planet_osm_polygon as osm 
   where 
     osm.building != '' and ST_Intersects(osm.way,ST_Transform(simple_buildings.geom, 900913)))
);
create index non_intersecting_buildings_geom_gist on non_intersecting_buildings using gist(geom);

create table intersecting_buildings as (
select 
  *
from 
  simple_buildings
where 
  exists 
  (select * 
   from 
     planet_osm_polygon as osm 
   where 
     osm.building != '' and ST_Intersects(osm.way,ST_Transform(simple_buildings.geom, 900913)))
);
create index intersecting_buildings_geom_gist on intersecting_buildings using gist(geom);

\q
''')



#
# Filter address points
#

print 'Filtering address points...'
p = subprocess.Popen('psql -d baltimore', 
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
print p.communicate(input='''
create table filtered_addresses as (
select 
  *
from 
  raw_addresses as addr
where 
  addr.ADDRPT_SRC != 'intersection'
  and addr.ADDRPT_SRC != 'Campus_bldg'
  and addr.ADDRPT_SRC != 'dpw_AddrPts'
  and addr.ADDRPT_SRC != 'lightrail'
  and addr.ADDRPT_SRC != 'subway_sta'
  and addr.FULL_ADDR != '0'
  and addr.ADDR_UNIT is null
  and addr.ADDR_NUMBE is not null
  and addr.ST_NAME is not null
);
create index filtered_addresses_geom_gist on filtered_addresses using gist(geom);

\q
''')



#
# Divide address points into those within non-intersecting buildings and
# those not
#

print 'Finding address points in buildings...'
p = subprocess.Popen('psql -d baltimore', 
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
print p.communicate(input='''
create table addresses_in_buildings as (
select 
  *
from 
  filtered_addresses as addr
where 
  exists 
  (select * 
   from 
     non_intersecting_buildings as bldg 
   where 
     ST_Intersects(addr.geom, bldg.geom))
);
create index addresses_in_buildings_geom_gist on addresses_in_buildings using gist(geom);

create table addresses_not_in_buildings as (
select 
  *
from 
  filtered_addresses as addr
where 
  not exists 
  (select * 
   from 
     non_intersecting_buildings as bldg 
   where 
     ST_Intersects(addr.geom, bldg.geom))
);
create index addresses_not_in_buildings_geom_gist on addresses_not_in_buildings using gist(geom);

\q
''')



#
# Join address point with building if building only contains one address point
# Create table with addresses from buildings containing multiple addresses
#

print 'Adding address points to buildings...'
p = subprocess.Popen('psql -d baltimore', 
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
print p.communicate(input='''
create table tmp_a as (
select distinct
  geom, addr_numbe, addr_frac, st_dir, st_name, st_type, zip_code
from
  addresses_in_buildings
);
alter table tmp_a add column gid serial;
update tmp_a set gid = default;

-- Select distict in both sort orders and intersect to find buildings with only one address
create table tmp_b as (
select distinct on (bldg.id)
  bldg.id, addr.addr_numbe, addr.addr_frac, addr.st_dir, addr.st_name, addr.st_type, addr.zip_code, addr.gid
from
  non_intersecting_buildings as bldg, tmp_a as addr
where
  ST_Intersects(addr.geom, bldg.geom)
order by
  bldg.id, addr.gid asc
);
create table tmp_c as (
select distinct on (bldg.id)
  bldg.id, addr.addr_numbe, addr.addr_frac, addr.st_dir, addr.st_name, addr.st_type, addr.zip_code, addr.gid
from
  non_intersecting_buildings as bldg, tmp_a as addr
where
  ST_Intersects(addr.geom, bldg.geom)
order by
  bldg.id, addr.gid desc
);
create table tmp_d as (select * from tmp_b intersect select * from tmp_c);

create table multiple_addresses_in_buildings as (
select
  addr.geom, addr.addr_numbe, addr.addr_frac, addr.st_dir, addr.st_name, addr.st_type, addr.zip_code
from
  tmp_a as addr
where
  not exists 
  (select * 
   from 
     tmp_d as bldg
   where 
     addr.gid = bldg.gid)
);

create table tmp_e as (
select
  *
from
  non_intersecting_buildings
left join
  tmp_d
using (id)
);
create table non_intersecting_buildings_addresses as (
select
  *
from
  tmp_e
);

drop table tmp_a;
drop table tmp_b;
drop table tmp_c;
drop table tmp_d;
drop table tmp_e;

\q
''')



#
# Find addresses that don't intersect with any buildings, existing or not
#

print 'Finding address points for empty lots...'
p = subprocess.Popen('psql -d baltimore', 
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
print p.communicate(input='''
create table empty_lot_addresses as (
select
  geom, addr_numbe, addr_frac, st_dir, st_name, st_type, zip_code
from
  addresses_not_in_buildings as addr
where
  not exists 
  (select * 
   from 
     intersecting_buildings as bldg 
   where 
     ST_Intersects(addr.geom, bldg.geom))
  and not exists
  (select * 
   from 
     planet_osm_polygon as osm 
   where 
     osm.building != '' and ST_Intersects(osm.way,ST_Transform(addr.geom, 900913)))
);

create table addresses_in_intersecting_or_existing_buildings_without_addresses as (
select
  geom, addr_numbe, addr_frac, st_dir, st_name, st_type, zip_code
from
  addresses_not_in_buildings as addr
where
  (exists 
  (select * 
   from 
     intersecting_buildings as bldg 
   where 
     ST_Intersects(addr.geom, bldg.geom))
  or exists
  (select * 
   from 
     planet_osm_polygon as osm 
   where 
     osm.building != '' and ST_Intersects(osm.way,ST_Transform(addr.geom, 900913))))
  and not exists
  (select *
   from
     planet_osm_polygon as osm 
   where 
     osm.building != '' and osm."addr:housenumber" != '' and osm."addr:housenumber" is not null and ST_Intersects(osm.way,ST_Transform(addr.geom, 900913)))
);

\q
''')



#
# Translate tags and output OSM file
#

print 'Creating OSM files...'
os.system('python ogr2osm.py -e 2248 -t bc-address.py -o multiple_addresses_in_buildings.osm --sql="select * from multiple_addresses_in_buildings" "PG:dbname=baltimore"')
os.system('python ogr2osm.py -e 2248 -t bc-address.py -o empty_lot_addresses.osm --sql="select * from empty_lot_addresses" "PG:dbname=baltimore"')
os.system('python ogr2osm.py -e 2248 -t bc-address.py -o addresses_in_intersecting_or_existing_buildings_without_addresses.osm --sql="select * from addresses_in_intersecting_or_existing_buildings_without_addresses" "PG:dbname=baltimore"')
os.system('python ogr2osm.py -e 2248 -t bc-address.py -o non_intersecting_buildings_addresses.osm --sql="select * from non_intersecting_buildings_addresses" "PG:dbname=baltimore"')
os.system('python ogr2osm.py -e 2248 -t bc-address.py -o intersecting_buildings.osm --sql="select * from intersecting_buildings" "PG:dbname=baltimore"')
