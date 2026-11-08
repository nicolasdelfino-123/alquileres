import {test} from 'node:test';
import assert from 'node:assert/strict';
import {deadlineState} from '../src/lib/deadline.js';
const state=(dueDate,extra={})=>deadlineState({dueDate,today:'2026-11-08',...extra});
test('payment deadlines advance from green through yellow to red',()=>{
 assert.equal(state('2026-11-28').tone,'green');
 assert.equal(state('2026-11-15').tone,'yellow');
 assert.equal(state('2026-11-10').tone,'red');
 assert.ok(state('2026-11-10').percent>state('2026-11-28').percent);
});
test('due today and overdue are distinguished',()=>{
 assert.equal(state('2026-11-08').text,'Vence hoy');
 assert.equal(state('2026-11-07').text,'Vencido hace 1 día');
 assert.equal(state('2026-11-01').percent,100);
});
test('settled and cancelled records never remain overdue',()=>{
 assert.equal(state('2026-01-01',{completed:true}).tone,'green');
 assert.equal(state('2026-01-01',{inactive:true}).tone,'neutral');
 assert.equal(state(null).text,'Sin fecha definida');
});
test('contract limits and leap-day arithmetic',()=>{
 assert.equal(state('2026-12-08',{windowDays:90,warningDays:30,dangerDays:7}).tone,'yellow');
 assert.equal(deadlineState({dueDate:'2028-03-01',today:'2028-02-28'}).days,2);
});
