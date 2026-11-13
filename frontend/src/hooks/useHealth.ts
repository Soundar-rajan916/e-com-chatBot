import { useEffect, useState } from 'react';
import { getHealth } from '../api/client';

export function useHealth() {
  const [isHealthy, setIsHealthy] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    let timerId: ReturnType<typeof setTimeout> | null = null;

    async function checkHealth() {
      try {
        const res = await getHealth();
        if (isMounted) {
          if (res.status === 'ok' && res.db === 'connected') {
            setIsHealthy(true);
            setErrorMessage(null);
          } else {
            setIsHealthy(false);
            setErrorMessage(`Service degraded: DB is ${res.db}`);
            scheduleRetry();
          }
        }
      } catch (err: unknown) {
        if (isMounted) {
          setIsHealthy(false);
          const msg = err instanceof Error ? err.message : 'Service unavailable';
          setErrorMessage(msg);
          scheduleRetry();
        }
      }
    }

    function scheduleRetry() {
      if (timerId) clearTimeout(timerId);
      timerId = setTimeout(() => {
        checkHealth();
      }, 10000);
    }

    checkHealth();

    return () => {
      isMounted = false;
      if (timerId) clearTimeout(timerId);
    };
  }, []);

  return { isHealthy, errorMessage };
}
