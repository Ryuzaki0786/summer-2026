const express =  require('express');
const {Pool} = require('pg');

const app =  express();

app.use(express.static('public'));

const pool = new Pool({
    user: 'ekam',
    password: 'VI.X.MMV',
    host: 'localhost',
    database: 'exoplanet',
    port: 5432
});

app.get('/planets',async(req,res) => {
    const result = await pool.query('SELECT * FROM planets LIMIT 50');
    res.json(result.rows);
});

app.get('/stats/methods',async(req,res) => {
    const result = await pool.query('SELECT discoverymethod, COUNT(*) as count FROM planets GROUP BY discoverymethod ORDER BY count DESC');
    res.json(result.rows);
});

app.get('/stats/kepler', async (req, res) => {
    const result = await pool.query(`
        SELECT pl_name, pl_orbper, pl_orbsmax,
               (pl_orbper * pl_orbper) / (pl_orbsmax * pl_orbsmax * pl_orbsmax) as kepler_ratio
        FROM planets
        WHERE pl_orbper IS NOT NULL 
          AND pl_orbsmax IS NOT NULL
          AND st_mass BETWEEN 0.9 AND 1.1
        ORDER BY pl_orbsmax
    `);
    res.json(result.rows);
});

app.get('/planets/search',async(req,res) => {
    const{method,min_mass,max_dist} = req.query;
    let query = 'SELECT * FROM planets WHERE 1=1';
    const params = [];

    if(method)
    {
        params.push(method);
        query += ` AND discoverymethod = $${params.length}`;
    }
    if(min_mass)
    {
        params.push(min_mass);
        query+= ` AND pl_bmassj >= $${params.length}`;
    }

    if(max_dist)
    {
        params.push(max_dist);
        query+= ` AND sy_dist <= $${params.length}`;
    }

    query+= ' LIMIT 100';
    const result =  await pool.query(query,params);
    res.json(result.rows);

});

app.get('/stats/habitable',async(req,res) => {
    const result = await pool.query(` SELECT pl_name, hostname, pl_orbsmax, st_teff, st_rad, sy_dist,
               ROUND((0.75 * SQRT(POWER(st_rad, 2) * POWER(st_teff / 5778.0, 4)))::numeric, 3) as hz_inner,
               ROUND((1.5 * SQRT(POWER(st_rad, 2) * POWER(st_teff / 5778.0, 4)))::numeric, 3) as hz_outer
        FROM planets
        WHERE pl_orbsmax IS NOT NULL 
          AND st_teff IS NOT NULL 
          AND st_rad IS NOT NULL
          AND pl_orbsmax BETWEEN 
              0.75 * SQRT(POWER(st_rad, 2) * POWER(st_teff / 5778.0, 4)) AND
              1.5 * SQRT(POWER(st_rad, 2) * POWER(st_teff / 5778.0, 4))
        ORDER BY sy_dist `);

        res.json(result.rows);
});

app.get('/stats/timeline',async(req,res) => {
    const result = await pool.query(` SELECT disc_year, 
            COUNT(*) as discovered,
            SUM(COUNT(*)) OVER (ORDER BY disc_year) as cumulative 
        FROM planets
        WHERE disc_year IS NOT NULL
        GROUP BY disc_year
        ORDER BY disc_year
        `);
        res.json(result.rows);
});

app.listen(3000, () => {
    console.log('Exoplanet API running on http://localhost:3000');
});