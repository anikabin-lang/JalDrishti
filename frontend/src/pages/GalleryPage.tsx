import React, { useCallback, useEffect, useState } from 'react';
import { PageContainer } from '../components/PageContainer';
import { Button } from '../components/Button';
import { Icon } from '../components/Icon';
import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import {
  AppRoute,
  HeritageImageSummary,
  InspectionSession,
  SiteSummary,
  StructureTypology,
} from '../types';
import {
  deleteInspectionImage,
  fetchGalleryImages,
  fetchSites,
  searchCloudinaryAssets,
  submitAnalysisRequest,
} from '../services/api';
import { useLanguage } from '../i18n/LanguageContext';

export interface GalleryPageProps {
  onRouteChange: (route: AppRoute) => void;
  onInspectionComplete?: (session: InspectionSession) => void;
}

type ViewMode = 'catalog' | 'cloud_search';

const TYPOLOGY_FILTERS: { value: string; label: string }[] = [
  { value: 'all', label: 'All Typologies' },
  { value: 'baoli', label: 'Baoli' },
  { value: 'bawari', label: 'Bawari' },
  { value: 'vav', label: 'Vav' },
  { value: 'kund', label: 'Kund' },
  { value: 'tank', label: 'Tank' },
  { value: 'other', label: 'Other' },
];

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

const formatDate = (isoString: string): string => {
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return isoString;
  }
};

export const GalleryPage: React.FC<GalleryPageProps> = ({
  onRouteChange,
  onInspectionComplete,
}) => {
  const { t } = useLanguage();
  const [viewMode, setViewMode] = useState<ViewMode>('catalog');
  const [images, setImages] = useState<HeritageImageSummary[]>([]);
  const [sites, setSites] = useState<SiteSummary[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [selectedSite, setSelectedSite] = useState<string>('all');
  const [selectedTypology, setSelectedTypology] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [pageOffset, setPageOffset] = useState<number>(0);
  const pageSize = 12;

  // Cloudinary Search cursor state
  const [nextCursor, setNextCursor] = useState<string | null>(null);

  // Modal inspection & analysis states
  const [inspectedImage, setInspectedImage] = useState<HeritageImageSummary | null>(null);
  const [analyzingImageId, setAnalyzingImageId] = useState<string | null>(null);
  const [deletingImageId, setDeletingImageId] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  // Load registered heritage sites
  const loadSites = useCallback(async () => {
    try {
      const res = await fetchSites();
      setSites(res.sites);
    } catch {
      // Non-critical: sites list can degrade gracefully
    }
  }, []);

  useEffect(() => {
    void loadSites();
  }, [loadSites]);

  // Load catalog images from local repository with filters
  const loadCatalogImages = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const siteFilter = selectedSite !== 'all' ? selectedSite : undefined;
      const typeFilter = selectedTypology !== 'all' ? selectedTypology : undefined;
      const res = await fetchGalleryImages({
        site_id: siteFilter,
        structure_type: typeFilter,
        limit: pageSize,
        offset: pageOffset,
      });

      // Filter locally if search query is provided
      let items = res.images;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        items = items.filter(
          (img) =>
            img.image_id.toLowerCase().includes(q) ||
            (img.site_id && img.site_id.toLowerCase().includes(q)) ||
            (img.inspection_id && img.inspection_id.toLowerCase().includes(q)) ||
            (img.original_filename && img.original_filename.toLowerCase().includes(q))
        );
      }

      setImages(items);
      setTotalCount(res.total);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not retrieve inspection images from heritage repository.'
      );
    } finally {
      setLoading(false);
    }
  }, [selectedSite, selectedTypology, searchQuery, pageOffset, pageSize]);

  // Perform live Cloudinary Search API query
  const loadCloudSearchImages = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const siteFilter = selectedSite !== 'all' ? selectedSite : undefined;
      const typeFilter = selectedTypology !== 'all' ? selectedTypology : undefined;
      const res = await searchCloudinaryAssets({
        query: searchQuery.trim() || undefined,
        site_id: siteFilter,
        tag: typeFilter,
        max_results: pageSize,
        next_cursor: nextCursor || undefined,
      });

      const mapped: HeritageImageSummary[] = res.resources.map((r) => ({
        image_id: r.public_id,
        site_id: r.site_id,
        inspection_id: r.inspection_id,
        public_id: r.public_id,
        asset_id: r.asset_id,
        format: r.format,
        width: r.width,
        height: r.height,
        bytes: r.bytes,
        created_at: r.created_at,
        status: 'cloud_stored',
        structure_type: typeFilter,
        preview_url: r.preview_url,
        thumbnail_url: r.thumbnail_url,
        original_url: r.secure_url,
      }));

      setImages(mapped);
      setTotalCount(res.total_count);
      setNextCursor(res.next_cursor || null);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : 'Cloudinary Search query failed. Check credentials or connection.'
      );
    } finally {
      setLoading(false);
    }
  }, [selectedSite, selectedTypology, searchQuery, nextCursor, pageSize]);

  useEffect(() => {
    if (viewMode === 'catalog') {
      void loadCatalogImages();
    } else {
      void loadCloudSearchImages();
    }
  }, [viewMode, loadCatalogImages, loadCloudSearchImages]);

  // Handle asset deletion
  const handleDeleteImage = async (img: HeritageImageSummary) => {
    const confirmDelete = window.confirm(
      `Permanently delete asset "${img.original_filename || img.image_id}" from Cloudinary and database?`
    );
    if (!confirmDelete) return;

    setDeletingImageId(img.image_id);
    setActionFeedback(null);
    try {
      await deleteInspectionImage(img.image_id);
      setActionFeedback(`Asset ${img.image_id} deleted successfully.`);
      if (inspectedImage?.image_id === img.image_id) {
        setInspectedImage(null);
      }
      // Refresh current view
      if (viewMode === 'catalog') {
        void loadCatalogImages();
      } else {
        void loadCloudSearchImages();
      }
      void loadSites();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Deletion failed.');
    } finally {
      setDeletingImageId(null);
    }
  };

  // Launch AI vision defect analysis on the chosen heritage image
  const handleRunAnalysis = async (img: HeritageImageSummary) => {
    setAnalyzingImageId(img.image_id);
    setActionFeedback(null);
    try {
      const typology = (img.structure_type as StructureTypology) || 'baoli';
      const result = await submitAnalysisRequest({
        imageId: img.image_id,
        structureType: typology,
        structureName: img.site_id
          ? img.site_id.replace(/_/g, ' ').replace(/-/g, ' ').toUpperCase()
          : 'Heritage Water Structure',
        region: 'Northern India',
      });

      if (onInspectionComplete) {
        onInspectionComplete({
          result,
          provenance: 'live',
          image: {
            image_id: img.image_id,
            inspection_id: img.inspection_id,
            site_id: img.site_id,
            status: 'ready',
            preview_url: img.preview_url,
            thumbnail_url: img.thumbnail_url,
            original_url: img.original_url,
            format: img.format,
            width: img.width,
            height: img.height,
            bytes: img.bytes,
            created_at: img.created_at,
          },
        });
      } else {
        onRouteChange('/analysis');
      }
    } catch (err: unknown) {
      alert(
        err instanceof Error
          ? `Analysis failed: ${err.message}`
          : 'Failed to complete vision analysis for this image.'
      );
    } finally {
      setAnalyzingImageId(null);
    }
  };

  return (
    <PageContainer
      title={t('gallery.title', 'Heritage Image Archive & Survey Gallery')}
      subtitle={t('gallery.subtitle', 'Complete lifecycle management of water heritage inspection imagery powered by Cloudinary.')}
      className="pb-24"
    >
      {/* Top Controls & Navigation Bar */}
      <section className="mb-8 flex flex-col gap-5 border-b border-ws-border pb-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs uppercase tracking-wider text-ws-muted">
                Section 05
              </span>
              <span className="h-1 w-1 rounded-full bg-ws-border" />
              <span className="text-xs text-amber-500 font-medium">{t('gallery.heading', 'Cloudinary Asset Management')}</span>
            </div>
            <h2 className="mt-1 font-display text-2xl font-light text-ws-text">
              {t('gallery.heading', 'Inspection Photographs & Cloud Storage')}
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <div className="inline-flex rounded-lg border border-ws-border bg-ws-card p-1">
              <button
                type="button"
                onClick={() => {
                  setViewMode('catalog');
                  setPageOffset(0);
                }}
                className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${
                  viewMode === 'catalog'
                    ? 'bg-ws-text text-ws-bg shadow-sm'
                    : 'text-ws-muted hover:text-ws-text'
                }`}
              >
                {t('gallery.databaseCatalog', 'Database Catalog')}
              </button>
              <button
                type="button"
                onClick={() => {
                  setViewMode('cloud_search');
                  setPageOffset(0);
                }}
                className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${
                  viewMode === 'cloud_search'
                    ? 'bg-ws-text text-ws-bg shadow-sm'
                    : 'text-ws-muted hover:text-ws-text'
                }`}
              >
                {t('gallery.cloudSearch', 'Cloudinary Live Search')}
              </button>
            </div>

            <Button
              variant="primary"
              size="sm"
              icon={<Icon name="upload" className="h-4 w-4" />}
              onClick={() => onRouteChange('/upload')}
            >
              {t('gallery.uploadNew', 'Upload New')}
            </Button>
          </div>
        </div>

        {/* Action feedback alert */}
        {actionFeedback && (
          <div className="flex items-center justify-between rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-2.5 text-xs text-emerald-400">
            <span>{actionFeedback}</span>
            <button
              type="button"
              onClick={() => setActionFeedback(null)}
              className="text-emerald-400 hover:text-emerald-300"
            >
              <Icon name="close" className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {/* Filter controls */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4">
          {/* Site Selector */}
          <div>
            <label htmlFor="site-select" className="mb-1 block text-xs font-mono uppercase text-ws-faint">
              {t('gallery.siteLabel', 'Heritage Site')}
            </label>
            <select
              id="site-select"
              value={selectedSite}
              onChange={(e) => {
                setSelectedSite(e.target.value);
                setPageOffset(0);
              }}
              className="w-full rounded-lg border border-ws-border bg-ws-card px-3 py-2 text-xs text-ws-text focus:border-ws-text focus:outline-none"
            >
              <option value="all">{t('gallery.allSites', 'All Sites')} ({totalCount})</option>
              {sites.map((s) => (
                <option key={s.site_id} value={s.site_id}>
                  {s.site_name} ({s.total_images} {t('gallery.photos', 'photos')})
                </option>
              ))}
            </select>
          </div>

          {/* Typology Selector */}
          <div>
            <label htmlFor="typology-select" className="mb-1 block text-xs font-mono uppercase text-ws-faint">
              {t('gallery.typologyLabel', 'Structure Typology')}
            </label>
            <select
              id="typology-select"
              value={selectedTypology}
              onChange={(e) => {
                setSelectedTypology(e.target.value);
                setPageOffset(0);
              }}
              className="w-full rounded-lg border border-ws-border bg-ws-card px-3 py-2 text-xs text-ws-text focus:border-ws-text focus:outline-none"
            >
              {TYPOLOGY_FILTERS.map((top) => (
                <option key={top.value} value={top.value}>
                  {top.value === 'all' ? t('gallery.allTypologies', 'All Typologies') : t('typology.' + top.value, top.label)}
                </option>
              ))}
            </select>
          </div>

          {/* Search Keywords */}
          <div className="sm:col-span-2">
            <label htmlFor="search-input" className="mb-1 block text-xs font-mono uppercase text-ws-faint">
              {t('gallery.searchLabel', 'Search by ID, File, or Session')}
            </label>
            <div className="flex gap-2">
              <input
                id="search-input"
                type="text"
                placeholder="e.g. agrasen, img_123, insp_delhi"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 rounded-lg border border-ws-border bg-ws-card px-3 py-2 text-xs text-ws-text placeholder-ws-faint focus:border-ws-text focus:outline-none"
              />
              {searchQuery && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setSearchQuery('')}
                >
                  {t('common.cancel', 'Clear')}
                </Button>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Main Content Area: Loading, Error, Empty, or Grid */}
      {loading ? (
        <div className="py-16">
          <LoadingState label={t('gallery.loading', 'Fetching Cloudinary heritage assets...')} />
        </div>
      ) : error ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-center">
          <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-rose-500/20 text-rose-400">
            <Icon name="alert" className="h-5 w-5" />
          </div>
          <h3 className="text-sm font-medium text-rose-300">{t('gallery.loadError', 'Unable to load image gallery')}</h3>
          <p className="mt-1 text-xs text-rose-200/70">{error}</p>
          <div className="mt-4 flex justify-center gap-3">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => (viewMode === 'catalog' ? void loadCatalogImages() : void loadCloudSearchImages())}
            >
              {t('common.tryAgain', 'Try Again')}
            </Button>
            <Button variant="primary" size="sm" onClick={() => onRouteChange('/upload')}>
              {t('analysis.startInspection', 'Go to Upload')}
            </Button>
          </div>
        </div>
      ) : images.length === 0 ? (
        <EmptyState
          visual={<Icon name="image" className="mb-4 h-10 w-10 text-ws-muted" />}
          title={t('gallery.noImagesFound', 'No inspection images found')}
          description={
            selectedSite !== 'all' || selectedTypology !== 'all' || searchQuery
              ? t('gallery.noImagesFiltered', 'No photographs match your active filter criteria. Try resetting filters.')
              : t('gallery.noImagesUploadPrompt', 'Start your heritage conservation campaign by uploading photographs for AI defect inspection.')
          }
          actions={
            <div className="flex gap-2">
              {(selectedSite !== 'all' || selectedTypology !== 'all' || searchQuery) && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setSelectedSite('all');
                    setSelectedTypology('all');
                    setSearchQuery('');
                  }}
                >
                  {t('gallery.resetFilters', 'Reset Filters')}
                </Button>
              )}
              <Button
                variant="primary"
                size="sm"
                icon={<Icon name="upload" className="h-4 w-4" />}
                onClick={() => onRouteChange('/upload')}
              >
                {t('gallery.uploadFirst', 'Upload First Image')}
              </Button>
            </div>
          }
        />
      ) : (
        <div className="space-y-6">
          {/* Card Grid */}
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {images.map((img) => {
              const isAnalyzing = analyzingImageId === img.image_id;
              const isDeleting = deletingImageId === img.image_id;

              return (
                <div
                  key={img.image_id}
                  className="group relative flex flex-col overflow-hidden rounded-xl border border-ws-border bg-ws-card transition-all hover:border-ws-text/30 hover:shadow-md"
                >
                  {/* Thumbnail Container */}
                  <div className="relative aspect-4/3 w-full overflow-hidden bg-ws-bg">
                    <img
                      src={img.thumbnail_url || img.preview_url}
                      alt={img.original_filename || img.image_id}
                      loading="lazy"
                      className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                    />

                    {/* Format and Resolution Pill */}
                    <div className="absolute bottom-2 left-2 flex items-center gap-1.5 rounded bg-black/70 px-2 py-0.5 text-[0.6875rem] font-mono text-white backdrop-blur-sm">
                      <span className="uppercase">{img.format}</span>
                      <span>•</span>
                      <span>
                        {img.width}×{img.height}
                      </span>
                    </div>

                    {/* Quick View Button Overlay */}
                    <button
                      type="button"
                      onClick={() => setInspectedImage(img)}
                      className="absolute right-2 top-2 rounded bg-black/60 p-1.5 text-white opacity-0 transition-opacity hover:bg-black/90 group-hover:opacity-100"
                      title={t('gallery.viewFull', 'View Full Resolution Original')}
                    >
                      <Icon name="crop" className="h-4 w-4" />
                    </button>
                  </div>

                  {/* Card Details */}
                  <div className="flex flex-1 flex-col p-4">
                    <div className="flex items-center justify-between gap-2">
                      <span className="rounded bg-ws-border/40 px-2 py-0.5 font-mono text-[0.6875rem] uppercase text-ws-muted">
                        {t('typology.' + (img.structure_type || 'baoli'), img.structure_type || 'baoli')}
                      </span>
                      <span className="font-mono text-[0.6875rem] text-ws-faint">
                        {formatBytes(img.bytes)}
                      </span>
                    </div>

                    <h4
                      className="mt-2 line-clamp-1 text-sm font-medium text-ws-text"
                      title={img.original_filename || img.image_id}
                    >
                      {img.original_filename || img.image_id}
                    </h4>

                    <div className="mt-1 flex items-center justify-between text-xs text-ws-muted">
                      <span className="line-clamp-1">
                        {img.site_id
                          ? img.site_id.replace(/_/g, ' ').replace(/-/g, ' ').toUpperCase()
                          : 'General Survey'}
                      </span>
                      <span className="font-mono text-[0.6875rem] text-ws-faint">
                        {formatDate(img.created_at)}
                      </span>
                    </div>

                    {/* Action Buttons */}
                    <div className="mt-4 flex items-center gap-2 border-t border-ws-border/60 pt-3">
                      <Button
                        variant="primary"
                        size="sm"
                        className="flex-1"
                        disabled={isAnalyzing || isDeleting}
                        onClick={() => void handleRunAnalysis(img)}
                        icon={
                          isAnalyzing ? (
                            <Icon name="refresh" className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Icon name="arrowRight" className="h-3.5 w-3.5" />
                          )
                        }
                      >
                        {isAnalyzing ? t('gallery.analyzing', 'Analyzing...') : t('gallery.inspectAi', 'Inspect AI')}
                      </Button>

                      <button
                        type="button"
                        onClick={() => setInspectedImage(img)}
                        className="rounded-lg border border-ws-border p-2 text-ws-muted hover:border-ws-text hover:text-ws-text"
                        title={t('gallery.viewFull', 'View Full Resolution Original')}
                      >
                        <Icon name="external" className="h-4 w-4" />
                      </button>

                      <button
                        type="button"
                        disabled={isDeleting}
                        onClick={() => void handleDeleteImage(img)}
                        className="rounded-lg border border-ws-border p-2 text-ws-muted hover:border-rose-500 hover:text-rose-400"
                        title={t('gallery.deleteAsset', 'Delete Asset from Cloudinary')}
                      >
                        {isDeleting ? (
                          <Icon name="refresh" className="h-4 w-4 animate-spin" />
                        ) : (
                          <Icon name="trash" className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination bar */}
          <div className="flex items-center justify-between border-t border-ws-border pt-4">
            <span className="font-mono text-xs text-ws-faint">
              {t('gallery.showing', 'Showing')} {images.length} {t('gallery.ofAssets', 'of')} {totalCount}
            </span>

            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={pageOffset === 0 || loading}
                onClick={() => setPageOffset((prev) => Math.max(0, prev - pageSize))}
                icon={<Icon name="arrowLeft" className="h-3.5 w-3.5" />}
              >
                {t('gallery.previous', 'Previous')}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={pageOffset + images.length >= totalCount || loading}
                onClick={() => setPageOffset((prev) => prev + pageSize)}
                icon={<Icon name="arrowRight" className="h-3.5 w-3.5" />}
              >
                {t('gallery.next', 'Next')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Lightbox for Original-Quality Inspection */}
      {inspectedImage && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
          onClick={() => setInspectedImage(null)}
        >
          <div
            className="relative flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-ws-border bg-ws-card shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-ws-border px-6 py-4">
              <div>
                <span className="font-mono text-xs uppercase text-ws-faint">
                  Cloudinary Full-Resolution Original
                </span>
                <h3 className="text-base font-medium text-ws-text">
                  {inspectedImage.original_filename || inspectedImage.image_id}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setInspectedImage(null)}
                className="rounded-lg p-2 text-ws-muted hover:bg-ws-bg hover:text-ws-text"
              >
                <Icon name="close" className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body: Uncompressed Image Display */}
            <div className="relative flex max-h-[60vh] items-center justify-center overflow-auto bg-black/90 p-4">
              <img
                src={inspectedImage.original_url || inspectedImage.preview_url}
                alt={inspectedImage.original_filename || inspectedImage.image_id}
                className="max-h-full max-w-full object-contain"
              />
            </div>

            {/* Modal Footer: Metadata & Actions */}
            <div className="flex flex-col gap-4 border-t border-ws-border bg-ws-bg px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs sm:grid-cols-4">
                <div>
                  <span className="text-ws-faint">{t('gallery.dimensions', 'Dimensions')}:</span>{' '}
                  <span className="font-mono text-ws-text">
                    {inspectedImage.width} × {inspectedImage.height}
                  </span>
                </div>
                <div>
                  <span className="text-ws-faint">{t('gallery.format', 'Format')}:</span>{' '}
                  <span className="font-mono uppercase text-ws-text">{inspectedImage.format}</span>
                </div>
                <div>
                  <span className="text-ws-faint">{t('gallery.fileSize', 'File Size')}:</span>{' '}
                  <span className="font-mono text-ws-text">{formatBytes(inspectedImage.bytes)}</span>
                </div>
                <div>
                  <span className="text-ws-faint">{t('gallery.uploaded', 'Uploaded')}:</span>{' '}
                  <span className="font-mono text-ws-text">{formatDate(inspectedImage.created_at)}</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <a
                  href={inspectedImage.original_url || inspectedImage.preview_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-lg border border-ws-border px-3 py-1.5 text-xs text-ws-text transition hover:bg-ws-card"
                >
                  <Icon name="external" className="h-3.5 w-3.5" />
                  {t('gallery.openRaw', 'Open Raw Link')}
                </a>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    void handleRunAnalysis(inspectedImage);
                    setInspectedImage(null);
                  }}
                  icon={<Icon name="arrowRight" className="h-3.5 w-3.5" />}
                >
                  {t('gallery.runVision', 'Run Vision AI')}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </PageContainer>
  );
};
