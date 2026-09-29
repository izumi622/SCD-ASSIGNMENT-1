import http from 'k6/http';
import { check, fail, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const base = __ENV.TARGET_URL || 'http://frontend-svc';
const errors = new Rate('application_errors');
export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '60s', target: 50 },
    { duration: '120s', target: 100 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    application_errors: ['rate<0.01'],
    http_req_duration: ['p(95)<2000'],
  },
};
export function setup() {
  const res = http.get(`${base}/ready`, { timeout: '10s' });
  if (res.status !== 200) fail('Application readiness failed before load');
}
export default function () {
  // Read-only, repeatable workload; no artificial CPU burner or invented complaints.
  for (const path of ['/api/complaints?page=1&page_size=10', '/api/stats', '/']) {
    const res = http.get(`${base}${path}`, { timeout: '10s', tags: { endpoint: path } });
    errors.add(res.status !== 200);
    check(res, { 'response is 200': r => r.status === 200 });
  }
  sleep(0.1);
}
export function handleSummary(data) {
  return { stdout: 'CIVICPULSE_SUMMARY=' + JSON.stringify(data) + '\n' };
}
