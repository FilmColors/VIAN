import * as THREE from '/static/three/build/three.module.js';
import Stats from '/static/three/jsm/libs/stats.module.js';
import { GUI } from '/static/three/jsm/libs/dat.gui.module.js';
import { DragControls } from '/static/three/jsm/controls/DragControls.js';
import { OrbitControls } from '/static/three/jsm/controls/OrbitControls.js';
import { TransformControls } from '/static/three/jsm/controls/TransformControls.js';
import { LineMaterial } from '/static/three/jsm/lines/LineMaterial.js';
import { LineGeometry } from '/static/three/jsm/lines/LineGeometry.js';
import { Line2 } from '/static/three/jsm/lines/Line2.js';

class ThreeJSView{
    constructor(frame_name, canvas_name, background_color = "rgb(255,255,255"){
        this.frame_name = frame_name; 
        this.canvas_name = canvas_name; 
        
        this.canvas = document.getElementById(canvas_name);
        this.frame = document.getElementById(frame_name);
        
        this.background_color = background_color

        const VERTEX_SCALE = 10;

        this.scene = new THREE.Scene();
        this.renderWidth = frame.clientWidth;
        this.renderHeight = frame.clientHeight;
        if (this.fov == null){
            this.fov = 75;
        }
        this.camera = new THREE.PerspectiveCamera(this.fov, this.renderWidth / this.renderHeight, 0.1, 1000);
        this.camera.updateProjectionMatrix();
        var currentCamera = this.camera;
        var ratio = this.renderHeight / this.renderWidth
        var orthoWidth = VERTEX_SCALE

        this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true });
        this.scene.background = new THREE.Color(this.background_color);
        this.renderer.setSize(this.renderWidth, this.renderHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.gammaInput = true;
        this.renderer.gammaOutput = true;
        this.renderer.shadowMap.enabled = true;

        var controls = new OrbitControls(this.camera, this.renderer.domElement);

        this.controls.damping = 0.5;
        this.controls.enableDamping = true; // an animation loop is required when either damping or auto-rotation are enabled
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = true;
        this.controls.minDistance = 1;
        this.controls.maxDistance = 500;
        this.controls.enablePan = false;
        this.controls.maxPolarAngle = Math.PI / 2;
        this.controls.target.set(VERTEX_SCALE / 2, 0, 0);

        var targetObject = new THREE.Object3D();
        this.scene.add(targetObject);

        var stats = new Stats();
        this.stats.showPanel(1);

        // this.frame.addEventListener("mousedown", function(){onClick()}, false);
        // this.frame.addEventListener("mouseup", function(){onRelease()}, false);
        // this.frame.addEventListener("onwheel", function(){onWheel()}, false);
        // this.canvas.onwheel = function(){onWheel(this)};

        this.gridHelper = new THREE.GridHelper(10, 10);
        this.scene.add(gridHelper);

        // gridLines(this);

        window.addEventListener('resize', function () { this.onWindowResize() }, false);
        this.frame.addEventListener('resize', function () { this.onWindowResize() }, false);
        // window.addEventListener('mousemove', function (event) { onMouseMove(event) }, false);
        this.renderer.render(this.scene, this.currentCamera);
    }

    animate(){
        requestAnimationFrame(function () { this.animate() });
    }

    onWindowResize() {
        var frame = this.frame;
        var width = frame.clientWidth;
        var height = width;

    
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }


}

export{
    ThreeJSView
}