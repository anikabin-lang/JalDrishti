import React, { useEffect, useMemo, useState } from 'react';
import { PageContainer } from '../components/PageContainer';
import { Section } from '../components/Section';
import { Button } from '../components/Button';
import { Icon } from '../components/Icon';
import { EmptyState } from '../components/EmptyState';
import { InspectionCanvas } from '../components/InspectionCanvas';
import { DefectLegend } from '../components/DefectLegend';
import { ProvenanceBanner } from '../components/ProvenanceBanner';
import { PipelineTriageAlert } from '../components/PipelineTriageAlert';
import { OriginTag } from '../components/StatusBadge';
import { AnalysisOverview } from '../components/analysis/AnalysisOverview';
import { FindingsSection } from '../components/analysis/FindingsSection';
import { ProbableCauses } from '../components/analysis/ProbableCauses';
import { EngineeringAssessment } from '../components/analysis/EngineeringAssessment';
import { MaterialCompatibility } from '../components/analysis/MaterialCompatibility';
import { RestorationStrategy } from '../components/analysis/RestorationStrategy';
import { TechnicalDetails } from '../components/analysis/TechnicalDetails';
import { AppRoute, InspectionSession } from '../types';
import { humanize, listEngineeringMetrics, readRootCauses, resolveImageSource, visionOrigin } from '../utils/analysis';
import { downloadInspectionPdf } from '../services/api';
import { useLanguage } from '../i18n/LanguageContext';

export interface AnalysisPageProps {
  session: InspectionSession | null;
  onRouteChange: (route: AppRoute) => void;
  onLoadFixture: () => void;
}

const scrollToSection = (id: string) => {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.getElementById(id)?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
};

export const AnalysisPage: React.FC<AnalysisPageProps> = ({ session, onRouteChange, onLoadFixture }) => {
  const { language, t } = useLanguage();
  const detections = session?.result.vision.detections ?? [];
  const classKey = detections.map((d) => d.class_name).join('|');
  const [visibleClasses, setVisibleClasses] = useState<Set<string>>(() => new Set(detections.map((d) => d.class_name)));
  const [highlighted, setHighlighted] = useState<number | null>(null);

  // Reset toggles when a different result is loaded.
  useEffect(() => {
    setVisibleClasses(new Set(detections.map((d) => d.class_name)));
    setHighlighted(null);
  }, [classKey, session?.result.metadata.created_at]);

  const metrics = useMemo(() => (session ? listEngineeringMetrics(session.result) : []), [session]);
  const causes = useMemo(() => (session ? readRootCauses(session.result) : []), [session]);

  if (!session) {
    return (
      <PageContainer
        eyebrow={t('analysis.eyebrow', 'JalDrishti / Findings')}
        title={t('analysis.title', 'Findings')}
        subtitle={t('analysis.subtitle', 'Detections, engineering scores and conservation considerations for one inspection.')}
        plate="well-octagon"
        treatment="panel"
        ground="dark"
      >
        <EmptyState
          title={t('analysis.noInspectionTitle', 'No inspection loaded')}
          description={
            <>
              <p>{t('analysis.noInspectionDesc', 'Run a photograph through the pipeline to see its findings here.')}</p>
              <p className="mt-2">
                {t(
                  'analysis.devSampleDesc',
                  'To review the interface without the backend, you can open the development sample. It is a fixed fixture, clearly labelled, and is not the result of any analysis.'
                )}
              </p>
            </>
          }
          actions={
            <>
              <Button onClick={() => onRouteChange('/upload')} icon={<Icon name="upload" className="h-4 w-4" />}>
                {t('analysis.startInspection', 'Start an inspection')}
              </Button>
              <Button variant="secondary" onClick={onLoadFixture}>
                {t('analysis.viewDevSample', 'View development sample')}
              </Button>
            </>
          }
        />
      </PageContainer>
    );
  }

  const { result } = session;
  const imageSrc = resolveImageSource(session);
  const title = result.structure.name || `${t('analysis.unnamed', 'Unnamed')} ${t('typology.' + result.structure.type, humanize(result.structure.type))}`;

  const toggleClass = (name: string) =>
    setVisibleClasses((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });

  return (
    <PageContainer
      eyebrow={t('analysis.eyebrow', 'JalDrishti / Findings')}
      title={title}
      subtitle={
        <>
          {t('typology.' + result.structure.type, humanize(result.structure.type))}
          {result.structure.region ? ` · ${result.structure.region}` : ''}
        </>
      }
      plate="well-octagon"
      treatment="panel"
      ground="dark"
      actions={
        <>
          <Button variant="secondary" onClick={() => onRouteChange('/upload')}>
            {t('analysis.newInspection', 'New inspection')}
          </Button>
          <Button
            variant="secondary"
            onClick={() => downloadInspectionPdf(session.image?.inspection_id || 'latest', language)}
            icon={<Icon name="download" className="h-4 w-4" />}
          >
            PDF Report ({language.toUpperCase()})
          </Button>
          <Button onClick={() => onRouteChange('/report')} icon={<Icon name="arrowRight" className="h-4 w-4" />} className="flex-row-reverse">
            {t('analysis.openReport', 'Open report')}
          </Button>
        </>
      }
      banner={<ProvenanceBanner session={session} />}
    >
      <AnalysisOverview result={result} onJump={scrollToSection} className="mb-20" />

      <div className="space-y-20">
        <Section
          id="findings"
          index="01"
          title={t('dash.keyFindings', 'Key findings')}
          description={
            result.vision.relevance_status === 'irrelevant'
              ? t('analysis.gateRejected', 'Inspection gate rejected this image as non-heritage subject matter.')
              : t('dash.keyFindingsDesc', 'What the vision model found in the photograph, ordered by relative image-space extent.')
          }
          aside={<OriginTag kind={visionOrigin(session)} />}
        >
          <PipelineTriageAlert vision={result.vision} className="mb-6" />
          {result.vision.relevance_status === 'irrelevant' ? (
            <div className="rounded-sm border border-dashed border-ink-300 p-8 text-center text-sm text-ink-600">
              <p className="font-semibold text-ink-800">{t('analysis.damageSuspended', 'Damage analysis suspended')}</p>
              <p className="mt-1 text-xs">
                {t(
                  'analysis.damageSuspendedDesc',
                  'Computer vision defect detection was withheld to prevent generating false damage records on non-heritage imagery.'
                )}
              </p>
              <div className="mt-4">
                <Button variant="secondary" onClick={() => onRouteChange('/upload')}>
                  {t('analysis.uploadHeritageImg', 'Upload a heritage structure image')}
                </Button>
              </div>
            </div>
          ) : (
            <FindingsSection
              detections={detections}
              scaleReference={result.vision.scale_reference}
              highlighted={highlighted}
              onHighlight={setHighlighted}
              canvas={
                <div className="space-y-4">
                  <InspectionCanvas
                    imageSrc={imageSrc}
                    imageDimensions={result.vision.image_dimensions}
                    detections={detections}
                    visibleClasses={visibleClasses}
                    highlighted={highlighted}
                    onHighlight={setHighlighted}
                  />
                  <DefectLegend detections={detections} visibleClasses={visibleClasses} onToggleClass={toggleClass} />
                  <p className="text-xs leading-relaxed text-ink-500">
                    {t(
                      'analysis.confidenceNote',
                      'Detection confidence is the model’s certainty that a region belongs to a class. It says nothing about how serious the defect is.'
                    )}
                  </p>
                </div>
              }
            />
          )}
        </Section>

        <Section
          id="causes"
          index="02"
          title={t('analysis.probableCauses', 'Probable causes')}
          description={t(
            'analysis.probableCausesDesc',
            'Inferred by deterministic rules from the findings above. Hypotheses to check on site, not diagnoses.'
          )}
          aside={<OriginTag kind={session.provenance === 'fixture' ? 'fixture' : 'rules'} />}
        >
          <ProbableCauses causes={causes} />
        </Section>

        <Section
          id="assessment"
          index="03"
          title={t('analysis.engineeringAssessment', 'Engineering assessment')}
          description={t(
            'analysis.engineeringAssessmentDesc',
            'Scores calculated by rule from image-space evidence. They describe what is visible, not structural safety.'
          )}
          aside={<OriginTag kind={session.provenance === 'fixture' ? 'fixture' : 'rules'} />}
        >
          <EngineeringAssessment metrics={metrics} />
        </Section>

        <Section
          id="materials"
          index="04"
          title={t('analysis.materialCompatibility', 'Material compatibility')}
          description={t(
            'dash.materialsDesc',
            'Candidate repair materials ranked against the assumed original, with a seven-dimension profile for comparison.'
          )}
          aside={
            <>
              <OriginTag kind={session.provenance === 'fixture' ? 'fixture' : 'rules'} />
              {result.material.verification_required && <OriginTag kind="expert" />}
            </>
          }
        >
          <MaterialCompatibility material={result.material} />
        </Section>

        <Section
          id="restoration"
          index="05"
          title={t('dash.restorationStrategy', 'Restoration strategy')}
          description={t(
            'analysis.restorationRoadmapDesc',
            'A phased starting point for planning. Every action requires review by a qualified conservation engineer before work begins.'
          )}
          aside={
            <>
              <OriginTag kind={session.provenance === 'fixture' ? 'fixture' : 'rules'} />
              <OriginTag kind="expert" />
            </>
          }
        >
          <RestorationStrategy restoration={result.restoration} />
        </Section>

        <Section
          id="technical"
          index="06"
          title={t('dash.technical', 'Technical details & references')}
          description={t('dash.technicalDesc', 'How this result was produced, and the sources its rules and planner cite.')}
        >
          <TechnicalDetails result={result} causes={causes} />
        </Section>
      </div>
    </PageContainer>
  );
};

export default AnalysisPage;
