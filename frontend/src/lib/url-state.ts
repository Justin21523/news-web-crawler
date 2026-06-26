"use client";

import type { ReadonlyURLSearchParams } from "next/navigation";

export function readQuery(search: ReadonlyURLSearchParams, key: string, fallback = "") {
  return search.get(key) ?? fallback;
}

export function updateQueryString(search: ReadonlyURLSearchParams, changes: Record<string, string | number | null | undefined>) {
  const next = new URLSearchParams(search.toString());
  Object.entries(changes).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") next.delete(key);
    else next.set(key, String(value));
  });
  return next.toString();
}

export function validParam<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback;
}
