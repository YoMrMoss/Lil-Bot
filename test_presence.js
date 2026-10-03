const fs = require('fs');
const assert = require('assert');
const source = fs.readFileSync(__dirname + '/display-preview.html', 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
new Function(source);
const body = source.slice(source.indexOf('function presenceMotion'), source.indexOf('function render'));
const motion = new Function(body + ';return presenceMotion;')();
for (const state of ['idle','typing','browsing','cat','helper','showoff','crying','nervous','rage','gaming','browsing_fast','music','orc','halloween_happy']) {
  assert.deepStrictEqual(motion(4000, state, false), motion(4000, 'idle', false));
  for (let t = 0; t < 16000; t += 50) {
    const m = motion(t, state, false);
    assert(Math.abs(m.x) <= 3 && Math.abs(m.y) <= 2);
  }
  assert.equal(motion(4000, state, true, 1).x, 0);
  assert.equal(motion(0, state, false, -1).x, -3);
}
assert.equal(motion(4000, 'sleep', false, 1).x, 0);
for (const state of ['time','weather','halloween_countdown','launch_chrome'])
  assert.deepStrictEqual(motion(4000, state, false), {x:0,y:0});
console.log('Preview syntax and shared presence motion passed');
