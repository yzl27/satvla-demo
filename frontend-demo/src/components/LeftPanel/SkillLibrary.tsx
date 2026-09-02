import { useState } from 'react';
import { TacticalPanel } from '../TacticalPanel';
import { TacticalToggle } from '../CyberControls';
import { skillLibraryTools } from '../../mockData';

export const SkillLibrary = () => {
  const [enabled, setEnabled] = useState<Set<string>>(
    new Set(skillLibraryTools.filter((t) => t.id === 'cv_tools').map((t) => t.id))
  );

  const toggle = (id: string) =>
    setEnabled((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <TacticalPanel title="工具技能库">
      <div className="grid grid-cols-2 gap-x-2 gap-y-3 mt-1">
        {skillLibraryTools.map((t) => (
          <TacticalToggle
            key={t.id}
            label={t.label}
            checked={enabled.has(t.id)}
            onChange={() => toggle(t.id)}
            title={t.desc}
          />
        ))}
      </div>
    </TacticalPanel>
  );
};
