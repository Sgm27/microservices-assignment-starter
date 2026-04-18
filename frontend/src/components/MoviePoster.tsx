import { useState } from "react";

type Props = {
  src?: string;
  title: string;
  className?: string;
  fallbackClassName?: string;
};

export default function MoviePoster({
  src,
  title,
  className,
  fallbackClassName,
}: Props) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    const cls = ["poster-fallback", fallbackClassName].filter(Boolean).join(" ");
    return (
      <div className={cls}>
        <span>{title}</span>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={title}
      className={className}
      onError={() => setFailed(true)}
    />
  );
}
