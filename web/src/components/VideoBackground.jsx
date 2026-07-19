import { useState, useEffect, useRef } from 'react';

const SCENES = [
  { label: 'Studio Lot',      src: '/studio-lot.mp4' },
  { label: 'Screening Room',  src: 'https://videos.pexels.com/video-files/3121459/3121459-uhd_2560_1440_24fps.mp4' },
  { label: 'Premiere Night',  src: 'https://videos.pexels.com/video-files/2022395/2022395-hd_1920_1080_30fps.mp4' },
];

export { SCENES };

export default function VideoBackground({ activeScene = 0 }) {
  const videoRefs = useRef([]);

  useEffect(() => {
    videoRefs.current.forEach(v => v?.play?.().catch(() => {}));
  }, []);

  return (
    <>
      {/* Video Stack — clipped to sit inside the bezel screen area */}
      <div className="fixed inset-0 z-0 bg-[#050508]"
           style={{
             clipPath: 'inset(clamp(40px,5vw,75px) clamp(30px,4vw,60px) clamp(45px,5.5vw,90px) clamp(30px,4vw,60px) round 40px)',
           }}>
        {SCENES.map((scene, i) => (
          <video
            key={i}
            ref={el => videoRefs.current[i] = el}
            src={scene.src}
            autoPlay
            muted
            loop
            playsInline
            className="absolute inset-0 w-full h-full object-cover transition-opacity duration-1000 ease-in-out"
            style={{ opacity: i === activeScene ? 1 : 0 }}
          />
        ))}
      </div>

      {/* Dark gradient for text legibility — same clip as video */}
      <div className="fixed inset-0 z-[1] bg-gradient-to-b from-black/60 via-black/30 to-black/70 pointer-events-none"
           style={{
             clipPath: 'inset(clamp(40px,5vw,75px) clamp(30px,4vw,60px) clamp(45px,5.5vw,90px) clamp(30px,4vw,60px) round 40px)',
           }} />

      {/* ── Old TV Bezel ── 3D border overlay */}
      <div className="fixed inset-0 z-50 pointer-events-none" aria-hidden="true">
        <svg width="0" height="0" className="absolute">
          <defs>
            <mask id="bezel-mask">
              <rect width="100%" height="100%" fill="white" />
              <rect
                style={{
                  x: 'clamp(30px, 4vw, 60px)',
                  y: 'clamp(40px, 5vw, 75px)',
                  width: 'calc(100% - (clamp(30px, 4vw, 60px) * 2))',
                  height: 'calc(100% - clamp(40px, 5vw, 75px) - clamp(45px, 5.5vw, 90px))',
                }}
                rx="40"
                ry="40"
                fill="black"
              />
            </mask>
          </defs>
        </svg>
        <div className="absolute inset-0 tv-bezel" style={{ WebkitMask: 'url(#bezel-mask)', mask: 'url(#bezel-mask)' }}>
          <div className="tv-bezel__screen" />
        </div>
      </div>
    </>
  );
}
