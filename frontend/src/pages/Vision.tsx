import { useEffect, useMemo, useRef, useState, type DragEvent } from 'react';
import { errorMessage, visionApi } from '../api';
import Gauge from '../components/Gauge';
import { ConfidenceBadge } from '../components/Signals';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardBody, CardHeader } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Icon } from '../components/ui/Icon';
import { Meter } from '../components/ui/Meter';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Segmented } from '../components/ui/Segmented';
import { Spinner } from '../components/ui/Spinner';
import { useToast } from '../components/ui/Toast';
import { copyText } from '../lib/clipboard';
import { cx } from '../lib/cx';
import { bytes, clamp01, isNum, num, pct, qualityTone, scoreTone, type Tone } from '../lib/format';
import { useTitle } from '../lib/useTitle';
import type { VisionAnalysis } from '../types';

const STEPS = [
  { title: 'Grayscale', body: 'Collapse RGB to luminance — removes colour noise and cuts the data 3×.' },
  { title: 'Denoise', body: 'Median / non-local-means filtering suppresses scanner speckle while keeping glyph edges.' },
  { title: 'Deskew', body: 'Estimate the dominant text angle (min-area rectangle / Hough lines) and rotate it level.' },
  { title: 'Adaptive threshold', body: 'Local Gaussian binarization copes with shadows and uneven lighting better than a global cut.' },
  { title: 'Morphological layout analysis', body: 'Dilate/close to merge glyphs into lines and blocks; grid lines mark tables, dense regions mark figures.' },
  { title: 'OCR', body: 'Recognize text per block with Tesseract / EasyOCR and average word confidences.' },
];

const BLOCK_COLORS: Record<string, string> = { text: '#0ea5e9', table: '#f59e0b', figure: '#a855f7' };
const IMAGE_ACCEPT = '.png,.jpg,.jpeg,.tiff,.bmp,.gif,.webp';

type ViewMode = 'annotated' | 'original';

const isSafeImageData = (s?: string | null): s is string => !!s && /^data:image\/(png|jpe?g|webp|gif);base64,/i.test(s);

export default function Vision() {
  useTitle('Vision Lab');
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<VisionAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>('annotated');
  const [step, setStep] = useState(-1);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    if (!loading) return;
    setStep(0);
    const t = window.setInterval(() => setStep((s) => (s + 1) % STEPS.length), 650);
    return () => window.clearInterval(t);
  }, [loading]);

  const analyze = async (f: File) => {
    setFile(f);
    setResult(null);
    setError(null);
    setLoading(true);
    try {
      const r = await visionApi.analyze(f);
      setResult(r);
      setView(isSafeImageData(r.annotated_image) || (r.blocks ?? []).length ? 'annotated' : 'original');
      toast.success('Image analyzed', f.name);
    } catch (e) {
      const msg = errorMessage(e, 'Analysis failed');
      setError(msg);
      toast.error('Vision analysis failed', msg);
    } finally {
      setLoading(false);
      setStep(-1);
    }
  };

  const pick = (list: FileList | null) => {
    const f = list?.[0];
    if (!f) return;
    if (!/\.(png|jpe?g|tiff?|bmp|gif|webp)$/i.test(f.name) && !f.type.startsWith('image/')) {
      toast.warning('Unsupported file', 'Choose a PNG, JPG, TIFF, BMP, GIF or WebP image.');
      return;
    }
    void analyze(f);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    pick(e.dataTransfer.files);
  };

  const blockCounts = useMemo(() => {
    const m: Record<string, number> = { text: 0, table: 0, figure: 0 };
    (result?.blocks ?? []).forEach((b) => {
      const t = (b.type || 'text').toLowerCase();
      m[t] = (m[t] ?? 0) + 1;
    });
    return Object.entries(m);
  }, [result]);
  const maxBlocks = Math.max(1, ...blockCounts.map(([, n]) => n));

  const q = result?.quality ?? null;
  const blur = q?.blur_score;
  const blurTone: Tone = !isNum(blur) ? 'neutral' : blur >= 300 ? 'success' : blur >= 100 ? 'warning' : 'danger';
  const bright = q?.brightness;
  const brightTone: Tone = !isNum(bright) ? 'neutral' : bright >= 0.35 && bright <= 0.9 ? 'success' : 'warning';
  const contrast = q?.contrast;
  const contrastTone: Tone = !isNum(contrast) ? 'neutral' : contrast >= 0.25 ? 'success' : contrast >= 0.15 ? 'warning' : 'danger';
  const skew = result?.skew_angle;
  const skewTone: Tone = !isNum(skew) ? 'neutral' : Math.abs(skew) < 1 ? 'success' : Math.abs(skew) < 3 ? 'warning' : 'danger';
  const W = result?.width ?? 0;
  const H = result?.height ?? 0;

  return (
    <Page>
      <PageHeader
        title="Vision Lab"
        description="See exactly what the computer-vision pipeline sees before text ever reaches the language model."
        actions={
          file ? (
            <Button icon="upload" onClick={() => inputRef.current?.click()} disabled={loading}>
              Analyze another
            </Button>
          ) : null
        }
      />
      <input
        ref={inputRef}
        type="file"
        accept={IMAGE_ACCEPT}
        className="sr-only"
        aria-label="Choose an image to analyze"
        onChange={(e) => {
          pick(e.target.files);
          e.target.value = '';
        }}
      />

      <div className="grid gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
        <Card className="h-max lg:sticky lg:top-20">
          <CardHeader icon="layers" title="Pipeline" description="OpenCV → OCR" />
          <CardBody>
            <ol className="space-y-3">
              {STEPS.map((s, i) => (
                <li key={s.title} className="flex gap-3">
                  <span
                    className={cx(
                      'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold tabular-nums transition-colors',
                      step === i ? 'border-accent bg-accent text-white' : result ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'border-line bg-elevated text-muted',
                    )}
                    aria-hidden="true"
                  >
                    {result && step < 0 ? <Icon name="check" className="h-3 w-3" strokeWidth={2.5} /> : i + 1}
                  </span>
                  <div>
                    <p className={cx('text-xs font-medium', step === i ? 'text-accent-soft' : 'text-fg')}>{s.title}</p>
                    <p className="mt-0.5 text-[11px] leading-relaxed text-muted">{s.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </CardBody>
        </Card>

        <div className="min-w-0 space-y-6">
          {!file ? (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              className={cx(
                'flex flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-16 text-center transition-colors',
                dragging ? 'border-accent bg-accent/[0.06]' : 'border-line-strong bg-surface',
              )}
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-line bg-elevated text-muted">
                <Icon name="image" className="h-5 w-5" />
              </div>
              <p className="mt-4 text-sm font-medium text-fg">Drop a scan, photo or screenshot</p>
              <p className="mt-1 text-xs text-muted">We’ll measure quality, detect layout blocks, deskew and OCR it.</p>
              <Button variant="primary" size="sm" className="mt-4" icon="upload" onClick={() => inputRef.current?.click()}>
                Choose image
              </Button>
            </div>
          ) : (
            <Card>
              <CardHeader
                icon="image"
                title={file.name}
                description={`${bytes(file.size)}${W && H ? ` · ${W} × ${H}px` : ''}`}
                actions={
                  result ? (
                    <Segmented<ViewMode>
                      label="Image view"
                      value={view}
                      onChange={setView}
                      options={[
                        { value: 'annotated', label: 'Detected blocks', icon: 'layers' },
                        { value: 'original', label: 'Original', icon: 'image' },
                      ]}
                    />
                  ) : null
                }
              />
              <div className="relative flex min-h-[260px] items-center justify-center bg-elevated/40 p-4">
                {view === 'annotated' && isSafeImageData(result?.annotated_image) ? (
                  <img src={result?.annotated_image ?? ''} alt="Input image with detected layout blocks outlined" className="max-h-[560px] max-w-full rounded-md border border-line object-contain" />
                ) : preview ? (
                  <div className="relative inline-block max-w-full">
                    <img src={preview} alt="Uploaded image" className="block max-h-[560px] max-w-full rounded-md border border-line" />
                    {view === 'annotated' && result && W > 0 && H > 0 && (result.blocks ?? []).length > 0 ? (
                      <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden="true">
                        {(result.blocks ?? []).map((b, i) => (
                          <rect
                            key={i}
                            x={b.x}
                            y={b.y}
                            width={b.w}
                            height={b.h}
                            fill={BLOCK_COLORS[b.type] ?? '#a1a1aa'}
                            fillOpacity="0.12"
                            stroke={BLOCK_COLORS[b.type] ?? '#a1a1aa'}
                            strokeWidth={Math.max(2, W / 400)}
                          />
                        ))}
                      </svg>
                    ) : null}
                  </div>
                ) : null}
                {loading ? (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-bg/60 backdrop-blur-[2px]">
                    <Spinner size="lg" className="text-accent" label="Analyzing image" />
                    <p className="text-xs text-muted">{step >= 0 ? STEPS[step].title : 'Analyzing'}…</p>
                  </div>
                ) : null}
              </div>
              {result && (result.blocks ?? []).length > 0 ? (
                <div className="flex flex-wrap gap-3 border-t border-line px-4 py-2 text-[11px] text-muted sm:px-5">
                  {Object.entries(BLOCK_COLORS).map(([t, c]) => (
                    <span key={t} className="inline-flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-sm border" style={{ borderColor: c, background: `${c}33` }} aria-hidden="true" />
                      {t}
                    </span>
                  ))}
                </div>
              ) : null}
            </Card>
          )}

          {error ? (
            <Card>
              <EmptyState icon="alert" title="Analysis failed" description={error} compact action={file ? <Button size="sm" onClick={() => void analyze(file)}>Retry</Button> : undefined} />
            </Card>
          ) : null}

          {result ? (
            <>
              <Card>
                <CardHeader
                  icon="target"
                  title="Image quality"
                  description="Measured before OCR; poor scans lower answer confidence"
                  actions={q?.quality ? <Badge tone={qualityTone(q.quality)}>{q.quality}</Badge> : null}
                />
                <CardBody className="grid grid-cols-2 gap-4 sm:grid-cols-5">
                  <Gauge value={isNum(q?.score) ? clamp01(q?.score ?? 0) : 0} label="Overall" display={pct(q?.score)} tone={scoreTone(q?.score)} sublabel="quality score" />
                  <Gauge value={isNum(blur) ? clamp01(blur / 600) : 0} label="Sharpness" display={isNum(blur) ? num(blur) : '—'} tone={blurTone} sublabel="Laplacian variance" />
                  <Gauge value={isNum(bright) ? clamp01(bright) : 0} label="Brightness" display={pct(bright)} tone={brightTone} sublabel="mean luminance" />
                  <Gauge value={isNum(contrast) ? clamp01(contrast / 0.5) : 0} label="Contrast" display={isNum(contrast) ? contrast.toFixed(2) : '—'} tone={contrastTone} sublabel="RMS contrast" />
                  <div className="col-span-2 flex flex-col items-center justify-center text-center sm:col-span-1">
                    <svg width="104" height="80" viewBox="0 0 104 80" role="img" aria-label={`Skew angle ${isNum(skew) ? skew.toFixed(1) : 'unknown'} degrees`}>
                      <line x1="12" y1="40" x2="92" y2="40" className="stroke-line" strokeWidth="2" strokeDasharray="4 4" />
                      <g transform={`rotate(${isNum(skew) ? Math.max(-25, Math.min(25, skew * 3)) : 0} 52 40)`}>
                        <rect x="22" y="22" width="60" height="36" rx="3" className="fill-elevated stroke-line-strong" strokeWidth="1.5" />
                        <line x1="30" y1="32" x2="74" y2="32" className={skewTone === 'success' ? 'stroke-emerald-500' : skewTone === 'warning' ? 'stroke-amber-500' : 'stroke-rose-500'} strokeWidth="2" />
                        <line x1="30" y1="40" x2="68" y2="40" className="stroke-subtle" strokeWidth="2" />
                        <line x1="30" y1="48" x2="72" y2="48" className="stroke-subtle" strokeWidth="2" />
                      </g>
                    </svg>
                    <div className="text-xs font-medium text-fg">Skew {isNum(skew) ? `${skew.toFixed(1)}°` : '—'}</div>
                    <div className="text-[11px] text-subtle">corrected before OCR</div>
                  </div>
                </CardBody>
              </Card>

              <div className="grid gap-6 md:grid-cols-[minmax(0,16rem)_minmax(0,1fr)]">
                <Card>
                  <CardHeader icon="layers" title="Layout blocks" description={`${(result.blocks ?? []).length} regions`} />
                  <CardBody>
                    <ul className="space-y-3">
                      {blockCounts.map(([t, n]) => (
                        <li key={t}>
                          <div className="mb-1 flex items-center justify-between text-xs">
                            <span className="inline-flex items-center gap-1.5 capitalize text-fg">
                              <span className="h-2 w-2 rounded-sm" style={{ background: BLOCK_COLORS[t] ?? '#a1a1aa' }} aria-hidden="true" />
                              {t}
                            </span>
                            <span className="tabular-nums text-muted">{n}</span>
                          </div>
                          <Meter value={n} max={maxBlocks} tone="accent" label={`${t} blocks: ${n}`} />
                        </li>
                      ))}
                    </ul>
                  </CardBody>
                </Card>

                <Card>
                  <CardHeader
                    icon="file"
                    title="OCR text"
                    description={[result.ocr?.engine, isNum(result.ocr?.words) ? `${num(result.ocr?.words)} words` : null].filter(Boolean).join(' · ') || 'Recognized text'}
                    actions={
                      <>
                        <ConfidenceBadge value={result.ocr?.confidence} label="OCR" />
                        {result.ocr?.text ? (
                          <Button
                            size="xs"
                            variant="ghost"
                            icon="copy"
                            onClick={async () => {
                              if (await copyText(result.ocr?.text ?? '')) toast.success('OCR text copied');
                            }}
                          >
                            Copy
                          </Button>
                        ) : null}
                      </>
                    }
                  />
                  <CardBody>
                    {result.ocr?.text ? (
                      <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-line bg-elevated/50 p-3 font-mono text-[12px] leading-relaxed text-fg">
                        {result.ocr.text}
                      </pre>
                    ) : (
                      <p className="text-sm text-subtle">No text recognized.</p>
                    )}
                  </CardBody>
                </Card>
              </div>

              <Card>
                <CardHeader icon="sparkles" title="Vision-LLM caption" description="What a multimodal model sees in the image" />
                <CardBody>
                  {result.caption ? (
                    <p className="text-sm leading-relaxed text-fg/90">{result.caption}</p>
                  ) : (
                    <p className="text-sm text-subtle">No vision LLM is configured on the backend — the pipeline above ran on classical CV + OCR only.</p>
                  )}
                </CardBody>
              </Card>
            </>
          ) : null}
        </div>
      </div>
    </Page>
  );
}
