import { Composition } from 'remotion';
import { SardisDemo } from './SardisDemo';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="SardisDemo"
        component={SardisDemo}
        durationInFrames={1800} // 60 seconds at 30fps
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
