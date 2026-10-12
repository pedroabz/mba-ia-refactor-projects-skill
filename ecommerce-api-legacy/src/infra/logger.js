/**
 * Structured logger: one JSON object per line, with a level and a timestamp.
 *
 * Replaces the `console.log` calls that were the project's only observability. Levels mean
 * verbosity can be turned down per environment, and structured fields mean the output is
 * parseable by a collector instead of only readable by a human.
 *
 * Never log a credential, a card number or a full request body — log identifiers.
 */
const LEVELS = { error: 10, warn: 20, info: 30, debug: 40 };

function createLogger({ level = 'info', stream = process.stdout } = {}) {
    const threshold = LEVELS[level] ?? LEVELS.info;

    function emit(levelName, message, fields) {
        if (LEVELS[levelName] > threshold) return;
        const entry = { ts: new Date().toISOString(), level: levelName, msg: message, ...fields };
        stream.write(`${JSON.stringify(entry)}\n`);
    }

    return {
        level,
        error: (message, fields) => emit('error', message, fields),
        warn: (message, fields) => emit('warn', message, fields),
        info: (message, fields) => emit('info', message, fields),
        debug: (message, fields) => emit('debug', message, fields),
    };
}

module.exports = { createLogger, LEVELS };
