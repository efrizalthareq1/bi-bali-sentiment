"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { SNAGraph, SNANode } from "@/lib/api";

type SimNode = SNANode & {
  x: number;
  y: number;
  vx: number;
  vy: number;
};

type Props = {
  data: SNAGraph;
  highlightId?: string | null;
  onSelectNode?: (node: SNANode | null) => void;
};

export function SNAForceCanvas({ data, highlightId, onSelectNode }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nodesRef = useRef<SimNode[]>([]);
  const [hovered, setHovered] = useState<string | null>(null);

  const edgeIndex = useMemo(() => {
    const map = new Map<string, { target: string; weight: number }[]>();
    for (const e of data.edges) {
      if (!map.has(e.source)) map.set(e.source, []);
      map.get(e.source)!.push({ target: e.target, weight: e.weight });
    }
    return map;
  }, [data.edges]);

  useEffect(() => {
    const w = 900;
    const h = 560;
    const clusterCenters: Record<string, { x: number; y: number }> = {
      positif: { x: w * 0.28, y: h * 0.28 },
      negatif: { x: w * 0.45, y: h * 0.72 },
      netral: { x: w * 0.72, y: h * 0.35 },
      media: { x: w * 0.78, y: h * 0.7 },
    };

    nodesRef.current = data.nodes.map((n, i) => {
      const c = clusterCenters[n.cluster] || { x: w / 2, y: h / 2 };
      const angle = (i / Math.max(data.nodes.length, 1)) * Math.PI * 2;
      const r = 40 + (i % 12) * 8;
      return {
        ...n,
        x: c.x + Math.cos(angle) * r,
        y: c.y + Math.sin(angle) * r,
        vx: 0,
        vy: 0,
      };
    });
  }, [data.nodes]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let frame = 0;
    let raf = 0;
    const nodeById = () => {
      const m = new Map<string, SimNode>();
      for (const n of nodesRef.current) m.set(n.id, n);
      return m;
    };

    const tick = () => {
      const nodes = nodesRef.current;
      const byId = nodeById();
      const w = canvas.width;
      const h = canvas.height;

      // Forces
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const minDist = 28;
          if (dist < minDist) {
            const f = ((minDist - dist) / dist) * 0.08;
            a.vx -= dx * f;
            a.vy -= dy * f;
            b.vx += dx * f;
            b.vy += dy * f;
          } else {
            const f = 0.0025 / dist;
            a.vx -= dx * f;
            a.vy -= dy * f;
            b.vx += dx * f;
            b.vy += dy * f;
          }
        }
      }

      for (const e of data.edges) {
        const a = byId.get(e.source);
        const b = byId.get(e.target);
        if (!a || !b) continue;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const ideal = 90 - Math.min(e.weight, 10) * 3;
        const f = ((dist - ideal) / dist) * 0.02;
        a.vx += dx * f;
        a.vy += dy * f;
        b.vx -= dx * f;
        b.vy -= dy * f;
      }

      // Cluster gravity
      const centers: Record<string, { x: number; y: number }> = {
        positif: { x: w * 0.28, y: h * 0.28 },
        negatif: { x: w * 0.45, y: h * 0.72 },
        netral: { x: w * 0.72, y: h * 0.35 },
        media: { x: w * 0.78, y: h * 0.7 },
      };
      for (const n of nodes) {
        const c = centers[n.cluster] || { x: w / 2, y: h / 2 };
        n.vx += (c.x - n.x) * 0.008;
        n.vy += (c.y - n.y) * 0.008;
        n.vx *= 0.85;
        n.vy *= 0.85;
        n.x += n.vx;
        n.y += n.vy;
        n.x = Math.max(20, Math.min(w - 20, n.x));
        n.y = Math.max(20, Math.min(h - 20, n.y));
      }

      // Draw
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#f8fafc";
      ctx.fillRect(0, 0, w, h);

      for (const e of data.edges) {
        const a = byId.get(e.source);
        const b = byId.get(e.target);
        if (!a || !b) continue;
        ctx.beginPath();
        ctx.strokeStyle = "rgba(100,116,139,0.28)";
        ctx.lineWidth = Math.min(2.5, 0.4 + e.weight * 0.15);
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }

      const active = highlightId || hovered;
      for (const n of nodes) {
        const r = 4 + Math.sqrt(n.size) * 2.2;
        const isActive = active === n.id;
        const dim = active && !isActive && !edgeIndex.get(active)?.some((x) => x.target === n.id) &&
          !data.edges.some((e) => e.target === active && e.source === n.id);
        ctx.beginPath();
        ctx.fillStyle = n.color;
        ctx.globalAlpha = dim ? 0.25 : 1;
        ctx.arc(n.x, n.y, isActive ? r + 2 : r, 0, Math.PI * 2);
        ctx.fill();
        if (isActive || n.size >= 8 || n.type === "keyword") {
          ctx.fillStyle = "#0f172a";
          ctx.font = `${isActive ? 12 : 10}px sans-serif`;
          ctx.fillText(n.label.slice(0, 28), n.x + r + 3, n.y + 3);
        }
        ctx.globalAlpha = 1;
      }

      frame += 1;
      if (frame < 220) {
        raf = requestAnimationFrame(tick);
      } else {
        // gentle idle redraw for hover
        raf = requestAnimationFrame(tick);
      }
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [data.edges, edgeIndex, highlightId, hovered]);

  const onMove = (ev: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = ((ev.clientX - rect.left) / rect.width) * canvas.width;
    const y = ((ev.clientY - rect.top) / rect.height) * canvas.height;
    let found: SimNode | null = null;
    for (const n of nodesRef.current) {
      const r = 6 + Math.sqrt(n.size) * 2.2;
      const dx = n.x - x;
      const dy = n.y - y;
      if (dx * dx + dy * dy <= r * r) {
        found = n;
        break;
      }
    }
    setHovered(found?.id || null);
  };

  const onClick = () => {
    if (!onSelectNode) return;
    const n = nodesRef.current.find((x) => x.id === hovered) || null;
    onSelectNode(n);
  };

  return (
    <canvas
      ref={canvasRef}
      width={900}
      height={560}
      className="h-auto w-full cursor-pointer rounded-xl border border-border bg-slate-50"
      onMouseMove={onMove}
      onMouseLeave={() => setHovered(null)}
      onClick={onClick}
    />
  );
}
