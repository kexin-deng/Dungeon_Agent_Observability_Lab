import { useEffect, useMemo, useState } from "react";

const BASE_INTERVAL_MS = 300;

export function useReplay(frames) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);

  const frameCount = frames.length;
  const currentFrame = frames[currentIndex];

  useEffect(() => {
    function onKeyDown(event) {
      if (event.target instanceof HTMLElement) {
        const tag = event.target.tagName.toLowerCase();
        if (tag === "input" || tag === "textarea" || event.target.isContentEditable) {
          return;
        }
      }

      if (event.code === "Space") {
        event.preventDefault();
        setIsPlaying((value) => !value);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        setIsPlaying(false);
        setCurrentIndex((value) => Math.min(value + 1, frameCount - 1));
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        setIsPlaying(false);
        setCurrentIndex((value) => Math.max(value - 1, 0));
      } else if (event.key.toLowerCase() === "r") {
        event.preventDefault();
        setIsPlaying(false);
        setCurrentIndex(0);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [frameCount]);

  useEffect(() => {
    if (!isPlaying || frameCount <= 1) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setCurrentIndex((value) => {
        if (value >= frameCount - 1) {
          setIsPlaying(false);
          return value;
        }
        return value + 1;
      });
    }, BASE_INTERVAL_MS / speed);

    return () => {
      window.clearInterval(timer);
    };
  }, [frameCount, isPlaying, speed]);

  return useMemo(
    () => ({
      currentFrame,
      currentIndex,
      isPlaying,
      speed,
      restart() {
        setCurrentIndex(0);
        setIsPlaying(false);
      },
      jumpTo(index) {
        setIsPlaying(false);
        setCurrentIndex(Math.max(0, Math.min(index, frameCount - 1)));
      },
      setSpeed,
      stepBack() {
        setIsPlaying(false);
        setCurrentIndex((value) => Math.max(value - 1, 0));
      },
      stepForward() {
        setIsPlaying(false);
        setCurrentIndex((value) => Math.min(value + 1, frameCount - 1));
      },
      togglePlay() {
        setIsPlaying((value) => !value);
      }
    }),
    [currentFrame, currentIndex, frameCount, isPlaying, speed]
  );
}
