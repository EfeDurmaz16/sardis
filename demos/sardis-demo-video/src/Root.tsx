import { Composition } from "remotion";
import { SardisDemoVideo } from "./SardisDemoVideo";

// 30 fps, 90 seconds = 2700 frames
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="SardisDemoVideo"
        component={SardisDemoVideo}
        durationInFrames={2700}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{}}
      />
      <Composition
        id="SardisDemoVideoShort"
        component={SardisDemoVideo}
        durationInFrames={1800}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ shortVersion: true }}
      />
    </>
  );
};
