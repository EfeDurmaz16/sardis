import { Composition } from 'remotion';
import { SardisDemo } from './SardisDemo';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="SardisYCDemo"
        component={SardisDemo}
        durationInFrames={5400}
        fps={60}
        width={1920}
        height={1080}
      />
    </>
  );
};
