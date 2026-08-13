"use client";

import { useCallback, useLayoutEffect, useRef, useState } from "react";

const BOTTOM_THRESHOLD_PX = 40;

function distanceFromBottom(el: HTMLElement): number {
  return el.scrollHeight - el.scrollTop - el.clientHeight;
}

export function useLogAutoScroll(lines: unknown[]) {
  const containerRef = useRef<HTMLDivElement>(null);
  const followTailRef = useRef(true);
  const lastScrollTopRef = useRef(0);
  const [isAtBottom, setIsAtBottom] = useState(true);

  const pauseFollow = useCallback(() => {
    followTailRef.current = false;
    setIsAtBottom(false);
  }, []);

  const resumeFollow = useCallback(() => {
    followTailRef.current = true;
    setIsAtBottom(true);
    const el = containerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, []);

  const jumpToLatest = useCallback(() => {
    followTailRef.current = true;
    setIsAtBottom(true);
    const el = containerRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, []);

  const hasSelectionInContainer = useCallback(() => {
    const sel = document.getSelection();
    if (!sel || sel.isCollapsed || !containerRef.current) return false;
    const node = sel.anchorNode;
    return node != null && containerRef.current.contains(node);
  }, []);

  const updateScrollPosition = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;

    // Scrolling up — stop following immediately
    if (el.scrollTop < lastScrollTopRef.current - 1) {
      pauseFollow();
    }

    lastScrollTopRef.current = el.scrollTop;

    const dist = distanceFromBottom(el);
    if (dist <= BOTTOM_THRESHOLD_PX) {
      followTailRef.current = true;
      setIsAtBottom(true);
    } else {
      followTailRef.current = false;
      setIsAtBottom(false);
    }
  }, [pauseFollow]);

  // After new lines render: only scroll if user is still at the bottom RIGHT NOW.
  // useLayoutEffect runs before paint so we don't flash/jump visibly.
  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    if (hasSelectionInContainer()) {
      pauseFollow();
      return;
    }

    const dist = distanceFromBottom(el);
    if (!followTailRef.current || dist > BOTTOM_THRESHOLD_PX) {
      followTailRef.current = false;
      setIsAtBottom(false);
      lastScrollTopRef.current = el.scrollTop;
      return;
    }

    el.scrollTop = el.scrollHeight;
    lastScrollTopRef.current = el.scrollTop;
    followTailRef.current = true;
    setIsAtBottom(true);
  }, [lines, hasSelectionInContainer, pauseFollow]);


  useLayoutEffect(() => {
    const onSelectionChange = () => {
      if (hasSelectionInContainer()) pauseFollow();
    };
    document.addEventListener("selectionchange", onSelectionChange);
    return () => document.removeEventListener("selectionchange", onSelectionChange);
  }, [hasSelectionInContainer, pauseFollow]);

  const scrollHandlers = {
    onScroll: updateScrollPosition,
    onWheel: (e: React.WheelEvent) => {
      if (e.deltaY < 0) pauseFollow();
    },
    onMouseDown: () => {
      const el = containerRef.current;
      if (!el) return;
      if (distanceFromBottom(el) > 2) pauseFollow();
    },
    onTouchStart: () => pauseFollow(),
    style: { overflowAnchor: "none" as const },
  };

  return { containerRef, isAtBottom, jumpToLatest, resumeFollow, scrollHandlers };
}
