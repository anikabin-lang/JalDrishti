import React from 'react';
import { VisionResultContract } from '../types';
import { Icon } from './Icon';
import { useLanguage } from '../i18n/LanguageContext';

interface PipelineTriageAlertProps {
  vision: VisionResultContract;
  className?: string;
}

export const PipelineTriageAlert: React.FC<PipelineTriageAlertProps> = ({ vision, className = '' }) => {
  const { t } = useLanguage();
  const {
    relevance_status,
    relevance_confidence,
    quality_status,
    rejection_reason,
    needs_manual_review,
    status_message,
    detections,
  } = vision;

  // Case 1: Out-of-Domain Non-Heritage Rejection
  if (relevance_status === 'irrelevant') {
    return (
      <div
        role="alert"
        className={`rounded-sm border border-laterite-500/60 bg-laterite-50 p-4 text-sm text-laterite-900 ${className}`}
      >
        <div className="flex items-start gap-3">
          <Icon name="close" className="mt-0.5 h-5 w-5 shrink-0 text-laterite-600" />
          <div className="space-y-1">
            <p className="font-semibold text-laterite-950">
              {t('triage.nonHeritageTitle', 'Inspection Halted: Non-Heritage Subject Matter Detected')}
            </p>
            <p className="text-xs leading-relaxed text-laterite-800">
              {rejection_reason ||
                t('triage.nonHeritageDefault', 'This image does not depict historic masonry, stepwells, or traditional water architecture.')}
            </p>
            <p className="text-[0.6875rem] font-mono uppercase tracking-wider text-laterite-700">
              {t('triage.nonHeritageConfidence', 'Non-Heritage Confidence')}: {typeof relevance_confidence === 'number' ? `${(relevance_confidence * 100).toFixed(1)}%` : 'High'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Case 2: Borderline / Manual Review Required
  if (needs_manual_review || relevance_status === 'uncertain') {
    return (
      <div
        role="alert"
        className={`rounded-sm border border-ochre-500/60 bg-ochre-50 p-4 text-sm text-ochre-900 ${className}`}
      >
        <div className="flex items-start gap-3">
          <Icon name="alert" className="mt-0.5 h-5 w-5 shrink-0 text-ochre-600" />
          <div className="space-y-1">
            <p className="font-semibold text-ochre-950">
              {t('triage.reviewTitle', 'Triage Notice: Expert Structural Review Recommended')}
            </p>
            <p className="text-xs leading-relaxed text-ochre-800">
              {t('triage.reviewDesc', 'The surface classification is borderline or uncertain. Automated bounding boxes should be verified against physical site conditions.')}
            </p>
            {status_message && (
              <p className="text-[0.6875rem] font-mono text-ochre-700">
                {status_message}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Case 3: Quality Warnings (Blur or Extreme Lighting)
  if (quality_status && quality_status !== 'good') {
    return (
      <div
        role="note"
        className={`rounded-sm border border-ink-300 bg-ink-50 p-4 text-sm text-ink-800 ${className}`}
      >
        <div className="flex items-start gap-3">
          <Icon name="alert" className="mt-0.5 h-5 w-5 shrink-0 text-ink-600" />
          <div className="space-y-1">
            <p className="font-semibold text-ink-950">
              {quality_status === 'blurred'
                ? t('triage.blurTitle', 'Image Quality Notice: Spatial Blur Detected')
                : t('triage.exposureTitle', 'Image Quality Notice: Extreme Exposure Detected')}
            </p>
            <p className="text-xs leading-relaxed text-ink-700">
              {quality_status === 'blurred'
                ? t('triage.blurDesc', 'High-frequency detail is diminished due to motion or defocus blur. Sub-millimeter hairline cracks may not be resolvable.')
                : t('triage.exposureDesc', 'Severe shadow or direct solar glare impairs contrast across masonry joints. Findings should be cross-referenced with diffuse daylight imagery.')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Case 4: Heritage Masonry with Zero Visible Defects
  if (relevance_status === 'relevant' && detections.length === 0) {
    return (
      <div
        role="status"
        className={`rounded-sm border border-jade-500/40 bg-jade-50/70 p-4 text-sm text-jade-900 ${className}`}
      >
        <div className="flex items-start gap-3">
          <Icon name="check" className="mt-0.5 h-5 w-5 shrink-0 text-jade-600" />
          <div className="space-y-1">
            <p className="font-semibold text-jade-950">
              {t('triage.intactTitle', 'Masonry Surface Integrity: No Active Structural Defects Identified')}
            </p>
            <p className="text-xs leading-relaxed text-jade-800">
              {t('triage.intactDesc', 'No fissures or biological intrusion exceed calibrated damage thresholds. Surface exhibits baseline stability under visual inspection.')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default PipelineTriageAlert;

