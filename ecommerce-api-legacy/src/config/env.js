/**
 * Minimal `.env` loader.
 *
 * Deliberately not a dependency: the project had none for this, and the whole feature is
 * "read KEY=VALUE lines into process.env if the file exists". Values already present in
 * the real environment always win, so a deployment never has its configuration shadowed
 * by a file that happens to be on disk.
 */
const fs = require('node:fs');
const path = require('node:path');

const LINE = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/;

function unquote(raw) {
    const value = raw.trim();
    const quoted = value.length >= 2 && (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
    );
    return quoted ? value.slice(1, -1) : value;
}

function loadEnvFile(file = path.resolve(__dirname, '..', '..', '.env')) {
    let contents;
    try {
        contents = fs.readFileSync(file, 'utf8');
    } catch (err) {
        if (err.code === 'ENOENT') return false;       // no .env is the normal case
        throw err;
    }

    for (const line of contents.split('\n')) {
        if (!line.trim() || line.trim().startsWith('#')) continue;
        const match = LINE.exec(line);
        if (!match) continue;
        const [, key, rawValue] = match;
        if (process.env[key] === undefined) {          // the real environment wins
            process.env[key] = unquote(rawValue);
        }
    }
    return true;
}

module.exports = { loadEnvFile };
