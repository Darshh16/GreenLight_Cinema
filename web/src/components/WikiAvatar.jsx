import { useState, useEffect } from 'react';

export default function WikiAvatar({ name, className }) {
  const [imgSrc, setImgSrc] = useState(null);
  
  useEffect(() => {
    let isMounted = true;
    
    // Default fallback is the UI Avatar (initials)
    const fallbackUrl = `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=2a1f14&color=D4A94E&rounded=true&size=64`;
    
    // Fetch from wikipedia API to try to get a real photo
    const url = `https://en.wikipedia.org/w/api.php?action=query&titles=${encodeURIComponent(name)}&prop=pageimages&format=json&pithumbsize=100&origin=*`;
    
    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (!isMounted) return;
        const pages = data.query?.pages;
        if (pages) {
          const pageId = Object.keys(pages)[0];
          // If Wikipedia has a thumbnail for this person, use it
          if (pages[pageId]?.thumbnail?.source) {
            setImgSrc(pages[pageId].thumbnail.source);
            return;
          }
        }
        setImgSrc(fallbackUrl);
      })
      .catch(() => {
        if (isMounted) setImgSrc(fallbackUrl);
      });
      
    return () => { isMounted = false; };
  }, [name]);
  
  if (!imgSrc) {
    return <div className={`animate-pulse bg-white/10 ${className}`}></div>;
  }
  
  return <img src={imgSrc} alt={name} className={`${className} object-cover`} />;
}
