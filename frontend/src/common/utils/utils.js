import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
	return twMerge(clsx(inputs));
}

export async function fetchJson(url) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`Fetch error: ${res.status}`);
  return await res.json();
}