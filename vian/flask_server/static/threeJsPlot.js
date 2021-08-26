import * as THREE from '/static/three/build/three.module.js';
import Stats from '/static/three/jsm/libs/stats.module.js';
import { GUI } from '/static/three/jsm/libs/dat.gui.module.js';
import { DragControls } from '/static/three/jsm/controls/DragControls.js';
import { OrbitControls } from '/static/three/jsm/controls/OrbitControls.js';
import { TransformControls } from '/static/three/jsm/controls/TransformControls.js';
import { LineMaterial } from '/static/three/jsm/lines/LineMaterial.js';
import { LineGeometry } from '/static/three/jsm/lines/LineGeometry.js';
import { Line2 } from '/static/three/jsm/lines/Line2.js';

function initScene(env, canvas_name, renderframe_name, isOrthographic = false) {
    const VERTEX_SCALE = 10;

    const canvas = document.getElementById(canvas_name);
    const frame = document.getElementById(renderframe_name);

    var scene = new THREE.Scene();

    var renderWidth = frame.clientWidth;
    var renderHeight = frame.clientHeight;
    if (env.fov == null){
        env.fov = 75;
    }
    console.log(renderHeight, renderWidth)
    var camera = new THREE.PerspectiveCamera(env.fov, renderWidth / renderHeight, 0.1, 1000);
    camera.updateProjectionMatrix();
    var currentCamera = camera;
    var ratio = renderHeight / renderWidth
    var orthoWidth = VERTEX_SCALE

    var cameraOrtho = new THREE.OrthographicCamera(-orthoWidth, orthoWidth, orthoWidth * ratio, -orthoWidth * ratio, -1000, 1000);
    cameraOrtho.updateProjectionMatrix();
    scene.add(cameraOrtho);

    var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
    scene.background = new THREE.Color("rgb(255,255,255)");
    renderer.setSize(renderWidth, renderHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.gammaInput = true;
    renderer.gammaOutput = true;
    renderer.shadowMap.enabled = true;

    // container.appendChild(renderer.domElement);
    var isOrthographic = isOrthographic;
    if (isOrthographic){
        currentCamera = cameraOrtho;
    }
    // Controls
    var controls = new OrbitControls(currentCamera, renderer.domElement);

    controls.damping = 0.5;
    controls.enableDamping = true; // an animation loop is required when either damping or auto-rotation are enabled
    controls.dampingFactor = 0.05;
    controls.screenSpacePanning = true;
    controls.minDistance = 1;
    controls.maxDistance = 500;
    controls.enablePan = false;
    controls.maxPolarAngle = Math.PI / 2;
    controls.target.set(VERTEX_SCALE / 2, 0, 0);

    var targetObject = new THREE.Object3D();
    scene.add(targetObject);

    var stats = new Stats();
    stats.showPanel(1);

    $("#renderControl").append(stats.dom);

    env.canvas = canvas;
    env.scene = scene;
    env.frame = frame;
    env.renderWidth = renderWidth;
    env.renderHeight = renderHeight;
    env.camera = camera;
    env.cameraOrtho = cameraOrtho;
    env.currentCamera = currentCamera;
    env.renderer = renderer;

    env.stats = stats;

    env.isOrthographic = isOrthographic;
    env.controls = controls;
    env.targetObject = targetObject;

    env.mode = 0
    env.currentMesh = null;

    env.items = new Map();
    env.labels = new Map();
    env.lights = new Map();

    env.hovered = null;
    env.hoveredOriginalColor = null;
    env.useHover = true;
    env.onHover = null

    env.onMove = null;

    env.isMovingListening=false;

    env.tooltip = null;
    env.lastMouse = new THREE.Vector2();
    env.getTooltip = null;
    env.useTooltip = false;
    env.tooltipMouseSensitivity = 0.005

    // An update function of the form func(env){}
    env.update = null;

    env.VERTEX_SCALE = VERTEX_SCALE;
    var raycaster = new THREE.Raycaster();
    var mouse = new THREE.Vector2();
    env.raycaster = raycaster;
    env.mouse = mouse;

    env.frame.addEventListener("mousedown", function(){onClick(env)}, false);
    env.frame.addEventListener("mouseup", function(){onRelease(env)}, false);
    env.frame.addEventListener("onwheel", function(){onWheel(env)}, false);
    env.canvas.onwheel = function(){onWheel(env)};

    // gridLines(env);

    window.addEventListener('resize', function () { onWindowResize(env) }, false);
    env.frame.addEventListener('resize', function () { onWindowResize(env) }, false);
    window.addEventListener('mousemove', function (event) { onMouseMove(event, env) }, false);
    env.renderer.render(env.scene, env.currentCamera);

    return env;
}

function onClick(env){
    if (env.onMove != null){
        env.isMovingListening = true;
    }
}

function onRelease(env){
    if (env.onMove != null){
        env.isMovingListening = false;
    }
}

function onWheel(env){
    if (env.onMove != null){
        env.onMove(env)
        console.log("Hello Wheel")
    }
}

function onWindowResize(env) {
    const frame = env.frame;
    const width = frame.clientWidth;
    var height = frame.clientHeight - 7;
    height = width;

    env.camera.aspect = width / height;
    env.camera.updateProjectionMatrix();
    env.renderer.setSize(width, height);
}

function onMouseMove(event, env) {
    var rect = env.renderer.domElement.getBoundingClientRect();
    env.mouse.x = ((event.clientX - rect.left) / (rect.right - rect.left)) * 2 - 1 - 0.01;
    env.mouse.y = - ((event.clientY - rect.top) / (rect.bottom - rect.top)) * 2 + 1 + 0.01;

    if (env.isMovingListening == true){
        env.onMove(env)
    }
}

function createTube(startVector, endVector, color, thickness) {
    // line material
    var curve = new THREE.LineCurve(
        startVector,
        endVector
    );
    var geometry = new THREE.TubeGeometry(curve, 20, 0.05, 8, true);
    var material = new THREE.MeshBasicMaterial({ color: color });
    var mesh = new THREE.Mesh(geometry, material);
    env.scene.add(env.mesh);
}

function clearScene(env) {
    env.items.forEach((elem) => {
        removeEntity(env, elem);
    });
    env.labels.forEach((elem) => {
        removeEntity(env, elem);
    });
}

function createObject(env, name, vertices, faces, colors) {
    let geometry = new THREE.Geometry();
    vertices.forEach(vertex => {
        geometry.vertices.push(
            new THREE.Vector3(
                vertex[0] * env.VERTEX_SCALE, 
                vertex[1] * env.VERTEX_SCALE, 
                vertex[2] * env.VERTEX_SCALE))
    })
    for (var i = 0; i < faces.length; i++) {
        var face = faces[i]
        var col = colors[i]
        col = [col[0] / 255, col[1] / 255, col[2] / 255]

        var f = new THREE.Face3(face[0], face[1], face[2])
        f.color = new THREE.Color(col[0], col[1], col[2]);
        f.vertexColors = new THREE.Color(col[0], col[1], col[2]);
        geometry.faces.push(f)
    }

    geometry.elementsNeedUpdate = true;
    geometry.computeBoundingSphere();
    geometry.computeBoundingBox();
    geometry.computeVertexNormals();
    geometry.computeFaceNormals();

    var mat = new THREE.MeshLambertMaterial({
        color: 0x00afaf,
        vertexColors: THREE.FaceColors,
    });

    mat.side = THREE.DoubleSide;
    var mesh = new THREE.Mesh(geometry, mat);
    mesh.name = name
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    
    return addObject(env, name, mesh);
}

function addObject(env, name, object) {
    object.name = name;

    if (env.items.has(name)) {
        removeEntity(env, env.items.get(name));
    }

    object.raycast_visible = true;
    env.items.set(name, object);
    env.scene.add(object);

    return object;
}

function removeObject(env, name) {
    if (env.items.has(name)) {
        removeEntity(env, env.items.get(name));
        env.items.delete(name);
        return true;
    }
    return false;
}

function removeEntity(env, object) {
    var selectedObject = env.scene.getObjectByName(object.name);
    env.scene.remove(selectedObject);

    if (object.geometry != null) {
        object.geometry.dispose();
    }

    if (object.material != null) {
        object.material.dispose();
        if (object.material.map != null) {
            object.material.map.dispose();
        }
    }
}

function addLabel(env, name, text, pos = new THREE.Vector3(), scale = 1.0, parameters = {}) {
    if (env.labels.has(name)) {
        removeEntity(env, env.labels.get(name));
    }
    let label = makeTextSprite(text, scale, parameters);

    label.name = name;
    label.position.set(pos.x, pos.y, pos.z);

    env.labels.set(name, label);
    env.scene.add(label);
    return label;
}

function addHtml(env, name, html, pos = new THREE.Vector3(), scale = 1.0) {
    if (env.labels.has(name)) {
        removeEntity(env, env.labels.get(name));
    }
    let spriteMaterial = new THREE.SpriteMaterial({ sizeAttenuation: false, depthTest : false });
    spriteMaterial.depthWrite = false;
    spriteMaterial.depthTest = false;

    let label = new THREE.Sprite(spriteMaterial);
    label.position.set(pos.x, pos.y, pos.z);

    initRenderHtmlSprite(html, label, scale);

    label.name = name;

    label.renderOrder = 0;
    env.labels.set(name, label);
    env.scene.add(label);
    return label;
}

function updateHtml(env, name, html, pos = null, scale=1.0) {
    let label = env.labels.get(name);
    if (label != null) {
        
        initRenderHtmlSprite(html, label, scale);
        if (pos != null) {
            label.position.set(pos.x, pos.y, pos.z);
        }
    }else{
        addHtml(env, name, html, pos, scale);
    }

}


function removeLabel(env, name) {
    if (env.labels.has(name)) {
        removeEntity(env, env.labels.get(name));
        env.labels.delete(name);
        return true;
    }
    return false;
}

function addLight(env, name, light, pos = new THREE.Vector3()) {
    if (env.lights.has(name)) {
        removeEntity(env, env.lights.get(name));
    }
    light.name = name;
    env.lights.set(name, light);
    env.scene.add(light);
    return light;
}

function removeLight(env, name) {
    if (env.lights.has(name)) {
        removeEntity(env, env.lights.get(name));
        env.lights.delete(name);
        return true;
    }
    return false;
}

function setCameraCenter(env, center) {
    env.controls.target.set(center.x, center.y, center.z);
    // env.controls.target.set(env.VERTEX_SCALE / 2, 0, 0);
    env.controls.update();
}

function roundRect(ctx, x, y, w, r) {
    ctx.beginPath(); ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
}

function makeTextSprite(message, scale, parameters) {
    if (parameters === undefined) parameters = {};
    var fontface = parameters.hasOwnProperty("fontface") ? parameters["fontface"] : "Arial";
    var fontsize = parameters.hasOwnProperty("fontsize") ? parameters["fontsize"] : 64;
    var borderThickness = parameters.hasOwnProperty("borderThickness") ? parameters["borderThickness"] : 4;
    var borderColor = parameters.hasOwnProperty("borderColor") ? parameters["borderColor"] : { r: 0, g: 0, b: 0, a: 1.0 };
    var backgroundColor = parameters.hasOwnProperty("backgroundColor") ? parameters["backgroundColor"] : { r: 100, g: 100, b: 100, a: 1.0 };
    var textColor = parameters.hasOwnProperty("textColor") ? parameters["textColor"] : { r: 0, g: 0, b: 0, a: 1.0 };

    var baseWidth = 400;

    var canvas = document.createElement('canvas');
    var context = canvas.getContext('2d');

    context.canvas.width = baseWidth;
    context.canvas.height = 200;

    context.font = "Bold " + fontsize + "px " + fontface;
    var metrics = context.measureText(message);
    var textWidth = metrics.width;

    context.fillStyle = "rgba(" + backgroundColor.r + "," + backgroundColor.g + "," + backgroundColor.b + "," + backgroundColor.a + ")";
    context.strokeStyle = "rgba(" + borderColor.r + "," + borderColor.g + "," + borderColor.b + "," + borderColor.a + ")";

    context.lineWidth = borderThickness;
    // roundRect(context, borderThickness/2, borderThickness/2, (textWidth + borderThickness) * 1.1, fontsize * 1.4 + borderThickness, 8);

    context.fillStyle = "rgba(" + textColor.r + ", " + textColor.g + ", " + textColor.b + ", 1.0)";
    context.fillText(message, borderThickness, fontsize + borderThickness);

    var texture = new THREE.Texture(canvas)
    texture.needsUpdate = true;
    texture.minFilter = THREE.LinearFilter;

    var spriteMaterial = new THREE.SpriteMaterial({ map: texture, sizeAttenuation: false });

    var sprite = new THREE.Sprite(spriteMaterial);
    sprite.scale.set(baseWidth / textWidth * (0.1 * scale), (0.1 * scale));

    sprite.position.x = (baseWidth / 2)

    return sprite;
}

function initRenderHtmlSprite(html, sprite, scale, parameters) {
    let texture_size = 512
    let textWidthMeasure = "HHH"
    if (parameters === undefined) parameters = {};
    var fontface = parameters.hasOwnProperty("fontface") ? parameters["fontface"] : "Arial";
    var fontsize = parameters.hasOwnProperty("fontsize") ? parameters["fontsize"] : 16;
    var borderThickness = parameters.hasOwnProperty("borderThickness") ? parameters["borderThickness"] : 4;
    var borderColor = parameters.hasOwnProperty("borderColor") ? parameters["borderColor"] : { r: 0, g: 0, b: 0, a: 1.0 };
    var backgroundColor = parameters.hasOwnProperty("backgroundColor") ? parameters["backgroundColor"] : { r: 100, g: 100, b: 100, a: 1.0 };
    var textColor = parameters.hasOwnProperty("textColor") ? parameters["textColor"] : { r: 0, g: 0, b: 0, a: 1.0 };

    var baseWidth = texture_size;

    var canvas = document.createElement('canvas');
    var context = canvas.getContext('2d');

    context.canvas.width = baseWidth;
    context.canvas.height = texture_size;

    // context.font = "Bold " + fontsize + "px " + fontface;
    var metrics = context.measureText(textWidthMeasure);
    var textWidth = metrics.width;

    context.fillStyle = "rgba(" + backgroundColor.r + "," + backgroundColor.g + "," + backgroundColor.b + "," + backgroundColor.a + ")";
    context.strokeStyle = "rgba(" + borderColor.r + "," + borderColor.g + "," + borderColor.b + "," + borderColor.a + ")";

    // roundRect(context, borderThickness/2, borderThickness/2, (textWidth + borderThickness) * 1.1, fontsize * 1.4 + borderThickness, 8);

    context.lineWidth = borderThickness;
    context.fillStyle = "rgba(" + textColor.r + ", " + textColor.g + ", " + textColor.b + ", 1.0)";

    renderHtmlToCanvas(html, sprite, canvas, context, 0, 0, context.canvas.width, context.canvas.height, texture_size)
    sprite.scale.set(20.0 * scale, 20.0 * scale);
    sprite.center.set(0.0, 1.0)
    return sprite;
}

function finalizeRenderHtmlSprite(sprite, canvas) {
    var texture = new THREE.Texture(canvas)
    texture.minFilter = THREE.LinearFilter;
    sprite.material.map = texture;
    texture.needsUpdate = true;
    sprite.material.needsUpdate = true;

    // var sprite = new THREE.Sprite( spriteMaterial );
    // sprite.scale.set(100 / 10 * 0.1, 0.1);
    // sprite.position.x = (100 / 2)
}

function renderHtmlToCanvas(html, sprite, canvas, ctx, x, y, width, height, texture_size) {
    var data =
        "data:image/svg+xml;charset=utf-8," +
        '<svg xmlns="http://www.w3.org/2000/svg" width="' + width + '" height="' + height + '">' +
        '<foreignObject width="100%" height="100%">' +
        html_to_xml(html) +
        '</foreignObject>' +
        '</svg>';
    var img = new Image();

    img.onload = function () {
        ctx.drawImage(img, 0, 0, texture_size, texture_size);
        finalizeRenderHtmlSprite(sprite, canvas)
    };
    img.onerror = function (e) {
        console.log(e)
    }
    img.src = data;
}

function html_to_xml(html) {
    var doc = document.implementation.createHTMLDocument('');
    doc.write(html);

    // You must manually set the xmlns if you intend to immediately serialize     
    // the HTML document to a string as opposed to appending it to a
    // <foreignObject> in the DOM
    doc.documentElement.setAttribute('xmlns', doc.documentElement.namespaceURI);

    // Get well-formed markup
    html = (new XMLSerializer).serializeToString(doc.body);
    return html;
}

function addLine(env, name, points, color = 0xff0000, width = 20) {
    var material2 = new THREE.LineBasicMaterial({
        color: color,
        linewidth: width
    });

/*     var geometry2 = new THREE.Geometry();
    points.forEach(element => {
        geometry2.vertices.push(element);
    }); */


    var matLine = new LineMaterial( {

        color: color,
        linewidth: width * 0.0002, // in pixels
        vertexColors: THREE.VertexColors,
        //resolution:  // to be set by renderer, eventually
        dashed: false

    } );

    var colors = []
    var positions = [];
    var c = new THREE.Color( color );

    points.forEach(element =>{
        positions.push(element.x, element.y, element.z);
        colors.push(c.r, c.g, c.b)
    })
    var geometry = new LineGeometry();
    geometry.setPositions(positions);
    geometry.setColors(colors);
    // points.forEach(element => {
    //     geometry.vertices.push(element);
    // }); 
    
    var line = new Line2( geometry, matLine );
    line.computeLineDistances();
    line.scale.set( 1, 1, 1 );



    // var line = new THREE.Line2( geometry, matLine );

    /* var line = new THREE.Line(geometry, matLine); */
    line = addObject(env, name, line)
    line.raycast_visible = false;
    return line
}

function gridLines(env) {
    var material2 = new THREE.LineBasicMaterial({
        color: 0xff0000,
        linewidth: 1
    });

    var geometry2 = new THREE.Geometry();
    geometry2.vertices.push(
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(1000, 0, 0)
    );

    var line_x = new THREE.Line(geometry2, material2);
    env.scene.add(line_x);

    var material3 = new THREE.LineBasicMaterial({
        color: 0x0000ff,
        linewidth: 1
    });

    var geometry3 = new THREE.Geometry();
    geometry3.vertices.push(
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(0, 100, 0),
    );

    var line_y = new THREE.Line(geometry3, material3);
    env.scene.add(line_y);

    var size = 10;
    var divisions = 10;

    var gridHelper = new THREE.GridHelper(size, divisions);
    env.scene.add(gridHelper);
}

function onOthographic(env) {
    env.currentCamera = env.cameraOrtho;
    env.isOrthographic = true;
    env.controls.camera = env.currentCamera;
    env.renderer.render(env.scene, env.currentCamera);
}

function onPerspective(env) {
    env.currentCamera = env.camera;
    env.controls.camera = env.currentCamera;
    env.isOrthographic = false;
    env.renderer.render(env.scene, env.currentCamera);
}

function addFloor(env) {
    var groundGeo = new THREE.PlaneBufferGeometry(10000, 10000);
    var groundMat = new THREE.MeshLambertMaterial({ color: 0xffffff });
    groundMat.color.setHSL(0.095, 1, 0.75);
    var ground = new THREE.Mesh(groundGeo, groundMat);
    ground.position.y = - 33;
    ground.rotation.x = - Math.PI / 2;
    ground.receiveShadow = true;
    env.scene.add(ground);
}

var animate = function (env) {
    env.stats.begin();

    if (env.update != null) {
        env.update(env);
    }
    requestAnimationFrame(function () { animate(env) });
    env.controls.update();

    if (env.useHover || env.useTooltip) {
        env.raycaster.setFromCamera(env.mouse, env.currentCamera);

        // calculate objects intersecting the picking ray var intersects =  
        // let items = Array.from(env.items.values());
        let items = [];
        env.items.forEach(element => {
            if (element.raycast_visible != null) {
                if (element.raycast_visible == true) {
                    items.push(element);
                }
            }
        });
        let intersects = env.raycaster.intersectObjects(items);

        if (env.useHover && env.onHover != null) {
            for (var i = 0; i < intersects.length; i++) {
                env.onHover(env, intersects[i].object);
            }
            if (intersects.length == 0){
                env.onHover(env, null);
            }
        }
        if (env.useTooltip) {
            if (Math.abs(env.lastMouse.x - env.mouse.x) >=env.tooltipMouseSensitivity 
             || Math.abs(env.lastMouse.y - env.mouse.y) >=env.tooltipMouseSensitivity){
                env.lastMouse = env.mouse.clone();
                if (intersects.length > 0) {
                    if (env.getTooltip != null) {
                        env.getTooltip(env, intersects[0]);
                    }
                }
            }

        }

    }

    // env.dirLight.position.copy( env.currentCamera.position );
    env.renderer.render(env.scene, env.currentCamera);

    env.stats.end();
};



export {
    initScene,
    onWindowResize,
    createTube,
    createObject,
    addObject,
    addLine,
    removeObject,
    removeEntity,
    addLabel,
    addHtml,
    updateHtml,
    removeLabel,
    addLight,
    removeLight,
    clearScene,
    roundRect,
    makeTextSprite,
    gridLines,
    onOthographic,
    onPerspective,
    addFloor,
    animate,
    setCameraCenter
};
// USAGE
// var env = {}
// initScene(env, "canvas", "renderframe");
// animate(env)